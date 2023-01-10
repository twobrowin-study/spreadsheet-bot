import sys

from telegram import Bot
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ChatMemberHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
)

from settings import BotToken

from log import Log, INFO, DEBUG
if len(sys.argv) > 1 and sys.argv[1] in ['debug', '--debug', '-D']:
    Log.setLevel(DEBUG)
    Debug = True
else:
    Log.setLevel(INFO)
    Debug = False

from sheets import (
    I18n,
    LogSheet,
    Switch,
    Settings,
    Groups,
    Users,
    Registration,
    Report,
    Keyboard,
    Notifications,
    PerfomNotification
)

from basic_handlers import ErrorHandlerFun, ChatMemberHandlerFun

UPDATE_GROUP_USER_REQUEST  = 0
UPDATE_GROUP_GROUP_REQUEST = 2
UPDATE_GROUP_CHAT_MEMBER   = 3

START_COMMAND  = 'start'
HELP_COMMAND   = 'help'
REPORT_COMMAND = 'report'

async def post_init(app: Application) -> None:
    await I18n.async_init()
    await LogSheet.async_init()
    await Switch.async_init()
    await Settings.async_init()
    await Groups.async_init()
    await Users.async_init()
    await Registration.async_init()
    await Report.async_init()
    await Keyboard.async_init()
    await Notifications.async_init()

    bot: Bot = app.bot
    await bot.set_my_commands([(HELP_COMMAND, Settings.help_command_description)])

    await LogSheet.write(None, "Started an application")

    app.create_task(Switch.update(app))
    app.create_task(Settings.update(app))
    app.create_task(Groups.update(app))
    app.create_task(Users.update(app))
    app.create_task(Registration.update(app))
    app.create_task(Report.update(app))
    app.create_task(Keyboard.update(app))
    app.create_task(Notifications.update(app))

    app.create_task(PerfomNotification(app))

async def post_shutdown(app: Application) -> None:
    await LogSheet.write(None, "Stopped an application")

if __name__ == '__main__':
    Log.info("Starting...")
    app = ApplicationBuilder() \
        .token(BotToken) \
        .concurrent_updates(True) \
        .post_init(post_init) \
        .post_shutdown(post_shutdown) \
        .build()

    app.add_error_handler(ErrorHandlerFun)

    ##
    # Chat member handlers
    ##
    app.add_handler(
        ChatMemberHandler(ChatMemberHandlerFun, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER, block=False),
        group=UPDATE_GROUP_CHAT_MEMBER
    )

    ##
    # Group handlers
    ##
    app.add_handler(
        CommandHandler(HELP_COMMAND, Groups.help_handler, filters=Groups.IsRegisteredFilter, block=False),
        group=UPDATE_GROUP_GROUP_REQUEST
    )

    app.add_handler(
        CommandHandler(REPORT_COMMAND, Groups.report_handler, filters=Groups.IsAdminFilter, block=False),
        group=UPDATE_GROUP_GROUP_REQUEST
    )

    ##
    # User handlers
    ##
    app.add_handler(
        MessageHandler(Users.IsRegistrationOverFilter, Users.registration_is_over_handler, block=False),
        group=UPDATE_GROUP_USER_REQUEST
    )

    app.add_handler(
        CommandHandler(START_COMMAND, Users.start_registration_handler, filters=Users.StartRegistrationFilter, block=False),
        group=UPDATE_GROUP_USER_REQUEST
    )

    app.add_handlers([
        CommandHandler(START_COMMAND, Users.restart_help_registration_handler, filters=Users.HasActiveRegistrationStateFilter, block=False),
        CommandHandler(HELP_COMMAND,  Users.restart_help_registration_handler, filters=Users.HasActiveRegistrationStateFilter, block=False),
        MessageHandler(Users.HasActiveRegistrationStateFilter, Users.proceed_registration_handler, block=False),
    ], group=UPDATE_GROUP_USER_REQUEST)
    
    app.add_handlers([
        CommandHandler(START_COMMAND, Users.restart_help_on_registration_complete_handler, filters=Users.HasNoRegistrationStateFilter, block=False),
        CommandHandler(HELP_COMMAND,  Users.restart_help_on_registration_complete_handler, filters=Users.HasNoRegistrationStateFilter, block=False),
    ], group=UPDATE_GROUP_USER_REQUEST)

    app.add_handler(MessageHandler(Users.KeyboardKeyInputFilter, Users.keyboard_key_handler, block=False), group=UPDATE_GROUP_USER_REQUEST)

    app.add_handlers([
        CallbackQueryHandler(Users.set_active_state_callback_handler, pattern=Users.CALLBACK_USER_ACTIVE_STATE_PATTERN, block=False),
        CallbackQueryHandler(Users.change_state_callback_handler,     pattern=Users.CALLBACK_USER_CHANGE_STATE_PATTERN, block=False),
        CommandHandler(START_COMMAND, Users.restart_help_change_state_handler, filters=Users.HasChangeRegistrationStateFilter, block=False),
        CommandHandler(HELP_COMMAND,  Users.restart_help_change_state_handler, filters=Users.HasChangeRegistrationStateFilter, block=False),
        MessageHandler(Users.HasChangeRegistrationStateFilter, Users.change_state_reply_handler, block=False),
    ], group=UPDATE_GROUP_USER_REQUEST)

    app.add_handlers([
        CommandHandler(START_COMMAND, Users.restart_help_notification_handler, filters=Users.HasAnyRegistrationStateFilter, block=False),
        CommandHandler(HELP_COMMAND,  Users.restart_help_notification_handler, filters=Users.HasAnyRegistrationStateFilter, block=False),
        MessageHandler(Users.HasAnyRegistrationStateFilter, Users.notification_reply_handler, block=False),
    ], group=UPDATE_GROUP_USER_REQUEST)

    app.add_handler(CallbackQueryHandler(Users.answer_callback_handler, pattern=Users.CALLBACK_USER_ANSWER_PATTERN, block=False))
    
    app.add_handler(MessageHandler(Users.StrangeErrorFilter, Users.strange_error_handler, block=False), group=UPDATE_GROUP_USER_REQUEST)

    app.run_polling()
    Log.info("Done. Goodby!")