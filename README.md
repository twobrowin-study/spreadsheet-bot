# Универсальный бот - библиотека и человек

[Пример таблицы - только на чтение](https://docs.google.com/spreadsheets/d/1dkpFEvOqWvVM_cJAnKvaQ0Ne8MmGPjy33cvPeeSwi-o/edit?usp=sharing)

## Функциональное наполнение - поддерживаемые таблицы

### Рубильник

Эта таблица предназначена для срочного выключения бота, поле `bot_active` выключает бота с исключением `BotShouldBeInactive`.

Поле `user_registration_open` заперщает регистрацию новых пользователей.

### Группы

Бота можно добавлять в группы, однако требуется ручное добавление идентификатора группы для использования ботом.

Идентификатор группы можно получить из таблицы `Логи`.

Группы могут иметь статус `is_admin` Нет, Да и Супер. Обычные группы получают все уведомления из таблицы `Оповещения`, админские группы - оповещения о количестве зарегистрированных пользователей и имею команду `/report` - будет выслано содержимое таблицы `Отчёт`.

Суперадминские группы также получают уведомления об ошибках:

* Общие ошибки

* Ошибки ввода пользователей

### Пользователи

Пользователи (таблица `Пользователи`) могут регистрировать в соответствии с описанием в таблице `Параметры регистрации`.

Также можно указать `state` для того чтобы пользователь ответил на конвретный вопрос - аналогично таблице `Оповещения`.

Пользователи имеют возможность изменить регистрационные данные при помощи таблицы `Клавиатура`

### Оповещения

Оповещения высылаются в установленную дату, возможно выслать картинку и указать поле, в которое таблицу будут сохранены ответы пользователей.

Возможно указать как ответ в текстовом формате, так и при помощи inline-клавиатуры в формате да/нет.

### Клавиатура

Клавиатура содержит описание показываемой зарегистрированному пользователю клавиатуры с помощью ввода.

Поддерживается функция (поле `function`) register для изменения регистрационных данных пользователя.

### Настройки, Логи, i18n

Настройки содержат все настройки приложения, в том числе текстовки стандартных сообщений пользователю.

В Логи записываются запуски, остановки приложения, добавления бота в группы, баны пользователей и ошибки ввода пользователя.

Интернационализация i18n содержит стандартные текстовки для переводов текстов.

## Запуск приложения

`eval $(tr "\n" "\t" < env) python main.py` в директории `python`

Для запуска в режиме отладки могут использоваться флаги `debug`, `--debug`, `-D`.

## Сборка и запуск Docker контейнера

`docker build -t twobrowin/spreadsheet-bot:latest .`

`docker push twobrowin/spreadsheet-bot:latest`

`ansible-playbook playbook.yaml -i hosts.ini`

Требуются дополнительные файлы:

* `hosts.ini` - описание подключение к хосту для развёртывания бота

* `secrets.yaml` - переменные `bot_token`, `sheet_acc_json`, `sheets_link`

## Переменные окружения для запуска приложения

* `BOT_TOKEN` - токен подключения к Telegram боту

* `SHEETS_ACC_JSON` - JWT токен подключения к Google Spreadsheet API

* `SHEETS_LINK` - Ссылка на подключение к требуемой таблице - боту требуется доступ на запись, может быть передан как в ссылке, так и назначен инстрементами Google Spreadsheet

* `SWITCH_UPDATE_TIME` - Время обновления стандартной таблицы 

* `SETTINGS_UPDATE_TIME` - Время обновления стандартной таблицы 