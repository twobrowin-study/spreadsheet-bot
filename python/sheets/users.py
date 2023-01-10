import pandas as pd
from sheets.sheet import AbstractSheetAdapter

from telegram import (
    Bot,
    Message,
    Update,
    Chat,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from sheets.i18n import I18n
from sheets.switch import Switch
from sheets.settings import Settings
from sheets.registration import Registration
from sheets.log import LogSheet
from sheets.groups import Groups
from sheets.report import Report
from sheets.keyboard import Keyboard
from sheets.notifications import Notifications
from log import Log

from datetime import datetime
import re

class UsersAdapterClass(AbstractSheetAdapter):
    CALLBACK_USER_SET_INACTIVE = 'user_set_inactive'
    CALLBACK_USER_SET_ACTIVE   = 'user_set_active'

    CALLBACK_USER_ANSWER_YES = 'user_answer_yes'
    CALLBACK_USER_ANSWER_NO  = 'user_answer_no'

    CALLBACK_USER_CHANGE_STATE_PREFIX  = 'user_change_'
    CALLBACK_USER_TEMPLATE             = 'user_change_{state}'

    CALLBACK_USER_ACTIVE_STATE_PATTERN = 'user_set_(in|)active'
    CALLBACK_USER_ANSWER_PATTERN       = 'user_answer_(yes|no)'
    CALLBACK_USER_CHANGE_STATE_PATTERN = 'user_change_.*'

    CALLBACK_USER_CHANGE_STATE_TEMPLATE   = '{user_change}_{state}@{message_id}'
    CALLBACK_USER_CHANGE_STATE_SEPARATORS = '_|@'

    def __init__(self) -> None:
        super().__init__('users', 'users', None, True)
        
        self.PrivateChatFilter                = self.PrivateChatClass(outer_obj=self)
        self.IsRegistrationOpenedFilter       = self.IsRegistrationOpenedClass(outer_obj=self)
        self.IsRegisteredFilter               = self.PrivateChatFilter & self.IsRegisteredClass(outer_obj=self)

        self.HasActiveRegistrationStateFilter = self.IsRegisteredFilter & self.HasActiveRegistrationStateClass(outer_obj=self)
        self.HasNoRegistrationStateFilter     = self.IsRegisteredFilter & self.HasNoRegistrationStateClass(outer_obj=self)
        self.HasChangeRegistrationStateFilter = self.IsRegisteredFilter & self.HasChangeRegistrationStateClass(outer_obj=self)
        self.HasAnyRegistrationStateFilter    = self.IsRegisteredFilter & self.HasAnyRegistrationStateClass(outer_obj=self)

        self.IsNotRegisteredFilter    = ~self.IsRegisteredFilter

        self.IsRegistrationOverFilter = self.PrivateChatFilter & ~self.IsRegistrationOpenedFilter & self.IsNotRegisteredFilter
        self.StartRegistrationFilter  = self.PrivateChatFilter &  self.IsRegistrationOpenedFilter & self.IsNotRegisteredFilter
        
        self.KeyboardKeyInputFilter = self.HasNoRegistrationStateFilter & self.InputInKeyboardKeysClass(outer_obj=self)
        
        self.StrangeErrorFilter = self.PrivateChatFilter & self.IsNotRegisteredFilter

        self.wks_row_pad = 2
        self.wks_col_pad = 1
        self.uid_col     = 'chat_id'

        self.state = lambda uid: self._get(self.selector(uid)).state
        self.active_user_count  = lambda: self.as_df.loc[self.as_df.is_active == I18n.yes].shape[0]
        self.should_send_report = lambda count: count % Report.send_every_x_active_users == 0

        self.is_active = lambda user: user.is_active == I18n.yes
        self.user_data_markdown = lambda user: "\n".join([
            f"{state}: *{user[state]}*"
            for state in Registration.main_states
        ]) + f"\n*{I18n.is_active if self.is_active(user) else I18n.is_inactive}*"
        self.user_data_inline_keyboard = lambda user: InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    user[state],
                    callback_data=self.CALLBACK_USER_TEMPLATE.format(state=state))
            ]
            for state in Registration.main_states
        ] + [[
            InlineKeyboardButton(
                I18n.set_inactive if self.is_active(user) else I18n.set_active,
                callback_data=self.CALLBACK_USER_SET_INACTIVE if self.is_active(user) else self.CALLBACK_USER_SET_ACTIVE
            )
        ]])
        self.selector_all_active = lambda: (
            (self.as_df.is_active == I18n.yes) &
            (self.as_df.is_bot_banned == I18n.no)
        )
    
    async def _pre_async_init(self):
        self.sheet_name = I18n.users
        self.update_sleep_time = Settings.users_update_time
    
    async def _get_df(self) -> pd.DataFrame:
        df = pd.DataFrame(await self.wks.get_all_records())
        df.chat_id = df.chat_id.apply(str)
        return df
    
    async def banned(self, chat_id: int|str):
        await self._update_record(chat_id, 'is_bot_banned', I18n.yes)
    
    async def unbanned(self, chat_id: int|str):
        await self._update_record(chat_id, 'is_bot_banned', I18n.no)
    
    async def _change_message_after_callback(self, chat_id: int|str, message_id: int|str, bot: Bot) -> None:
        try:
            user = self._get(self.selector(chat_id))
            keyboard_row = Keyboard.registration_keyboard_row
            await bot.edit_message_text(
                keyboard_row.text_markdown.format(user=self.user_data_markdown(user)),
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=self.user_data_inline_keyboard(user),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            Log.debug(f"Was not able to edit a message for chat id {chat_id}")
    
    async def send_to_all_users_and_set_state(self, bot: Bot, message: str, parse_mode: str, 
        send_photo: str = None, reply_state: str = None, is_text_reply: str = ''
    ):
        reply_markup = None
        if is_text_reply == I18n.yes:
            reply_markup = ReplyKeyboardRemove()
        elif is_text_reply == I18n.no:
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton(I18n.yes, callback_data=self.CALLBACK_USER_ANSWER_YES)],
                [InlineKeyboardButton(I18n.no,  callback_data=self.CALLBACK_USER_ANSWER_NO)],
            ])
        
        await self._send_to_all_uids(
            self.selector_all_active(),
            bot, message, parse_mode,
            send_photo,
            reply_markup=reply_markup
        )
        if is_text_reply == I18n.yes and reply_state != '' and reply_state != None:
            self.as_df.loc[self.selector_all_active(), 'state'] = reply_state
            wks_rows = self.as_df.loc[self.selector_all_active()].index.values + self.wks_row_pad
            wks_col  = self.wks_col('state')
            wks_update = self._prepare_batch_update([
                (wks_row, wks_col, reply_state)
                for wks_row in wks_rows
            ])
            await self.wks.batch_update(wks_update)
    
    class PrivateChatClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            return message.chat.type == Chat.PRIVATE
    
    class IsRegistrationOpenedClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            return Switch.user_registration_open
    
    class IsRegisteredClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            return self.outer_obj.exists(message.chat_id)

    class HasActiveRegistrationStateClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            df = self.outer_obj.as_df
            return not df.loc[
                (self.outer_obj.selector(message.chat_id)) &
                (df.state.isin(Registration.states))
            ].empty

    class HasNoRegistrationStateClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            df = self.outer_obj.as_df
            return not df.loc[
                (self.outer_obj.selector(message.chat_id)) &
                (df.state == '')
            ].empty

    class HasChangeRegistrationStateClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            df = self.outer_obj.as_df
            return not df.loc[
                (self.outer_obj.selector(message.chat_id)) &
                (df.state.str.startswith(I18n.user_change))
            ].empty

    class HasAnyRegistrationStateClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            df = self.outer_obj.as_df
            return not df.loc[
                (self.outer_obj.selector(message.chat_id)) &
                (df.state != '')
            ].empty
    
    class InputInKeyboardKeysClass(AbstractSheetAdapter.AbstractFilter):
        def filter(self, message: Message) -> bool:
            return message.text in Keyboard.keys
    
    async def registration_is_over_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_markdown(Settings.registration_is_over, reply_markup=ReplyKeyboardRemove())
        
    async def start_registration_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        registration_first = Registration.first
        
        await update.message.reply_markdown(Settings.start_template.format(
            template = registration_first.question
        ), reply_markup=ReplyKeyboardRemove())
        
        await self._batch_update_or_create_record(update.effective_chat.id,
            datetime      = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            username      = update.effective_chat.username,
            is_bot_banned = I18n.no,
            state         = registration_first.state,
        )
    
    async def restart_help_registration_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        registration = Registration.get(self.state(update.effective_chat.id))
        template = Settings.user_template_from_update(update)
        await update.message.reply_markdown(
            template.format(template = registration.question),
            reply_markup=registration.reply_keyboard
        )
    
    async def proceed_registration_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        state = self.state(update.effective_chat.id)
        registration_next = Registration.get_next(state)

        last_main_state = (state == Registration.last_main_state)
        last_state      = (state == Registration.last_state)

        if last_state:
            await update.message.reply_markdown(Settings.registration_complete, reply_markup=Keyboard.reply_keyboard)
        else:
            await update.message.reply_markdown(registration_next.question, reply_markup=registration_next.reply_keyboard)

        update_vals = {state: update.message.text}
        if last_main_state:
            update_vals['is_active'] = I18n.yes
        
        await self._batch_update_or_create_record(update.effective_chat.id,
            state = '' if last_state else registration_next.state,
            **update_vals
        )

        count = self.active_user_count()
        if last_main_state and self.should_send_report(count):
            context.application.create_task(
                Groups.send_to_all_admin_groups(
                    context.bot,
                    Report.currently_active_users_template.format(count=count),
                    ParseMode.MARKDOWN
                )
            )
    
    async def restart_help_on_registration_complete_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        template = Settings.user_template_from_update(update)
        await update.message.reply_markdown(
            template.format(template = Settings.restart_on_registration_complete),
            reply_markup=Keyboard.reply_keyboard
        )
    
    async def keyboard_key_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        keyboard_row = Keyboard.get(update.message.text)
        if keyboard_row.function == Keyboard.REGISTER_FUNCTION:
            user = self._get(self.selector(update.effective_chat.id))
            await update.message.reply_markdown(
                keyboard_row.text_markdown.format(user=self.user_data_markdown(user)),
                reply_markup=self.user_data_inline_keyboard(user)
            )
        elif keyboard_row.send_picture == '':
            await update.message.reply_markdown(
                keyboard_row.text_markdown,
                reply_markup=Keyboard.reply_keyboard
            )
        elif keyboard_row.send_picture != '':
            await update.message.reply_photo(
                keyboard_row.send_picture,
                caption=keyboard_row.text_markdown,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboard.reply_keyboard
            )
    
    async def set_active_state_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        await context.bot.send_message(
            update.effective_chat.id,
            I18n.has_been_set_inactive if update.callback_query.data == self.CALLBACK_USER_SET_INACTIVE else I18n.has_been_set_active,
            reply_markup=Keyboard.reply_keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        await self._update_record(update.effective_chat.id, 'is_active',
            I18n.no if update.callback_query.data == self.CALLBACK_USER_SET_INACTIVE else I18n.yes
        )
        await self._change_message_after_callback(update.effective_chat.id, update.callback_query.message.message_id, context.bot)
    
    async def change_state_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        state = update.callback_query.data.removeprefix(self.CALLBACK_USER_CHANGE_STATE_PREFIX)
        await context.bot.send_message(
            update.effective_chat.id,
            Settings.user_change_callback_reply_template.format(state=state),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN
        )
        await self._update_record(update.effective_chat.id, 'state',
            self.CALLBACK_USER_CHANGE_STATE_TEMPLATE.format(
                user_change = I18n.user_change,
                state       = state,
                message_id  = update.callback_query.message.message_id,
            )
        )
    
    async def restart_help_change_state_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        template = Settings.user_template_from_update(update)
        complex_state = self.state(update.effective_chat.id)
        _,state,_ = re.split(self.CALLBACK_USER_CHANGE_STATE_SEPARATORS, complex_state)
        await update.message.reply_markdown(
            template.format(template = Settings.user_change_callback_reply_template.format(state=state)),
            reply_markup=ReplyKeyboardRemove()
        )
    
    async def change_state_reply_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        complex_state = self.state(update.effective_chat.id)
        _,state,message_id = re.split(self.CALLBACK_USER_CHANGE_STATE_SEPARATORS, complex_state)
        await update.message.reply_markdown(
            Settings.user_change_message_reply_template.format(state=state),
            reply_markup=Keyboard.reply_keyboard
        )
        await self._batch_update_or_create_record(update.effective_chat.id,
            state = '',
            **{
                state: update.message.text
            }
        )
        await self._change_message_after_callback(update.effective_chat.id, message_id, context.bot)
    
    async def restart_help_notification_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        template = Settings.user_template_from_update(update)
        state = self.state(update.effective_chat.id)
        await update.message.reply_markdown(
            template.format(template = Notifications.get_text_markdown(state)),
            reply_markup=ReplyKeyboardRemove()
        )
    
    async def notification_reply_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        state = self.state(update.effective_chat.id)
        await update.message.reply_markdown(Notifications.get_reply_answer(state), reply_markup=ReplyKeyboardRemove())
        await self._batch_update_or_create_record(update.effective_chat.id,
            state = '',
            **{state: update.message.text}
        )
    
    async def answer_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        answer_yes = update.callback_query.data == self.CALLBACK_USER_ANSWER_YES
        await context.bot.send_message(
            update.effective_chat.id,
            Notifications.reply_to_yes if answer_yes else Notifications.reply_to_no,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboard.reply_keyboard
        )
        state = Notifications.get_reply_state(update.callback_query.message.text_markdown)
        await self._update_record(update.effective_chat.id, state, I18n.yes if answer_yes else I18n.no)
    
    async def strange_error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_markdown(Settings.strange_user_error, reply_markup=ReplyKeyboardRemove())
        message = (
            f"Strange error on user with id `{update.effective_chat.id}` "
            f"and username `{update.effective_chat.username}` "
            f"- user is not registered, but the bot is active"
        )
        Log.info(message)
        context.application.create_task(
            LogSheet.write(update.effective_chat.id, (
                f"Strange error, user {update.effective_chat.username} "
                f"is not registered, but the bot is active"
            ))
        )
        context.application.create_task(
            Groups.send_to_all_superadmin_groups(context.bot, message, ParseMode.MARKDOWN)
        )

Users = UsersAdapterClass()
