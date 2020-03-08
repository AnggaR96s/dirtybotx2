from typing import Union, List, Optional

from future.utils import string_types
from telegram import ParseMode, Update, Bot, Chat, User
from telegram.ext import CommandHandler, RegexHandler, Filters
from telegram.utils.helpers import escape_markdown

from hitsuki import dispatcher, spamfilters, OWNER_ID
from hitsuki.modules.helper_funcs.handlers import CMD_STARTERS
from hitsuki.modules.helper_funcs.misc import is_module_loaded
from hitsuki.modules.connection import connected

from hitsuki.modules import languages
from hitsuki.modules.helper_funcs.alternate import send_message

FILENAME = __name__.rsplit(".", 1)[-1]

# If module is due to be loaded, then setup all the magical handlers
if is_module_loaded(FILENAME):
    from hitsuki.modules.helper_funcs.chat_status import user_admin, is_user_admin
    from telegram.ext.dispatcher import run_async

    from hitsuki.modules.sql import disable_sql as sql

    DISABLE_CMDS = []
    DISABLE_OTHER = []
    ADMIN_CMDS = []

    class DisableAbleCommandHandler(CommandHandler):
        def __init__(self, command, callback, admin_ok=False, **kwargs):
            super().__init__(command, callback, **kwargs)
            self.admin_ok = admin_ok
            if isinstance(command, string_types):
                DISABLE_CMDS.append(command)
                if admin_ok:
                    ADMIN_CMDS.append(command)
            else:
                DISABLE_CMDS.extend(command)
                if admin_ok:
                    ADMIN_CMDS.extend(command)
            sql.disableable_cache(command)

        def check_update(self, update):
            chat = update.effective_chat  # type: Optional[Chat]
            user = update.effective_user  # type: Optional[User]
            if super().check_update(update):
                # Should be safe since check_update passed.
                command = update.effective_message.text_html.split(None, 1)[0][1:].split('@')[0]
                
                # disabled, admincmd, user admin
                if sql.is_command_disabled(chat.id, command.lower()):
                    is_disabled = command in ADMIN_CMDS and is_user_admin(chat, user.id)
                    if not is_disabled and sql.is_disable_del(chat.id):
                        update.effective_message.delete()
                    return is_disabled

                # not disabled
                else:
                    return True

            return False


    class DisableAbleRegexHandler(RegexHandler):
        def __init__(self, pattern, callback, friendly="", **kwargs):
            super().__init__(pattern, callback, **kwargs)
            DISABLE_OTHER.append(friendly or pattern)
            sql.disableable_cache(friendly or pattern)
            self.friendly = friendly or pattern

        def check_update(self, update):
            chat = update.effective_chat
            return super().check_update(update) and not sql.is_command_disabled(chat.id, self.friendly)


    @run_async
    @user_admin
    def disable(bot: Bot, update: Update, args: List[str]):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return

        conn = connected(bot, update, chat, user.id, need_admin=True)
        if conn:
            chat = dispatcher.bot.getChat(conn)
            chat_id = conn
            chat_name = dispatcher.bot.getChat(conn).title
        else:
            if update.effective_message.chat.type == "private":
                send_message(update.effective_message, languages.tl(update.effective_message, "You can do this command in groups, not PM"))
                return ""
            chat = update.effective_chat
            chat_id = update.effective_chat.id
            chat_name = update.effective_message.chat.title

        if len(args) >= 1:
            disable_cmd = args[0]
            if disable_cmd.startswith(CMD_STARTERS):
                disable_cmd = disable_cmd[1:]

            if disable_cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                sql.disable_command(chat.id, disable_cmd)
                if conn:
                    text = languages.tl(update.effective_message, "Disabled the use of `{}` in *{}*").format(disable_cmd, chat_name)
                else:
                    text = languages.tl(update.effective_message, "Disabled the use of `{}`").format(disable_cmd)
                send_message(update.effective_message, text,
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "That command can't be disabled"))

        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "What should I disable?"))


    @run_async
    @user_admin
    def enable(bot: Bot, update: Update, args: List[str]):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return

        conn = connected(bot, update, chat, user.id, need_admin=True)
        if conn:
            chat = dispatcher.bot.getChat(conn)
            chat_id = conn
            chat_name = dispatcher.bot.getChat(conn).title
        else:
            if update.effective_message.chat.type == "private":
                send_message(update.effective_message, languages.tl(update.effective_message, "You can do this command in groups, not PM"))
                return ""
            chat = update.effective_chat
            chat_id = update.effective_chat.id
            chat_name = update.effective_message.chat.title

        if len(args) >= 1:
            enable_cmd = args[0]
            if enable_cmd.startswith(CMD_STARTERS):
                enable_cmd = enable_cmd[1:]

            if sql.enable_command(chat.id, enable_cmd):
                if conn:
                    text = languages.tl(update.effective_message, "Enabled the use of `{}` in *{}*").format(enable_cmd, chat_name)
                else:
                    text = languages.tl(update.effective_message, "Enabled the use of `{}`").format(enable_cmd)
                send_message(update.effective_message, text,
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "Is that even disabled?"))

        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "What should I enable?"))


    @run_async
    @user_admin
    def list_cmds(bot: Bot, update: Update):
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return

        if DISABLE_CMDS + DISABLE_OTHER:
            result = ""
            for cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                result += " - `{}`\n".format(escape_markdown(cmd))
            send_message(update.effective_message, languages.tl(update.effective_message, "The following commands are toggleable:\n{}").format(result),
                                                parse_mode=ParseMode.MARKDOWN)
        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "No commands can be disabled."))

    @run_async
    @user_admin
    def disable_del(bot: Bot, update: Update):
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return

        msg = update.effective_message
        chat = update.effective_chat

        if len(msg.text.split()) >= 2:
            args = msg.text.split(None, 1)[1]
            if args == "yes" or args == "on":
                sql.disabledel_set(chat.id, True)
                send_message(update.effective_message, languages.tl(update.effective_message, "When command was disabled, I *will delete* that message."), parse_mode="markdown")
                return
            elif args == "no" or args == "off":
                sql.disabledel_set(chat.id, False)
                send_message(update.effective_message, languages.tl(update.effective_message, "When command was disabled, I *will not delete* that message."), parse_mode="markdown")
                return
            else:
                send_message(update.effective_message, languages.tl(update.effective_message, "The argument is not known - please use 'yes' or 'no'."))
        else:
            send_message(update.effective_message, languages.tl(update.effective_message, "Current disable del settings: *{}*").format("Enabled" if sql.is_disable_del(chat.id) else "Disabled"), parse_mode="markdown")


    # do not async
    def build_curr_disabled(chat_id: Union[str, int]) -> str:
        disabled = sql.get_all_disabled(chat_id)
        if not disabled:
            return languages.tl(chat_id, "No commands are disabled!")

        result = ""
        for cmd in disabled:
            result += " - `{}`\n".format(escape_markdown(cmd))
        return languages.tl(chat_id, "The following commands are currently restricted:\n{}").format(result)


    @run_async
    def commands(bot: Bot, update: Update):
        chat = update.effective_chat
        user = update.effective_user
        spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id, update.effective_message)
        if spam == True:
            return

        conn = connected(bot, update, chat, user.id, need_admin=True)
        if conn:
            chat = dispatcher.bot.getChat(conn)
            chat_id = conn
            chat_name = dispatcher.bot.getChat(conn).title
        else:
            if update.effective_message.chat.type == "private":
                send_message(update.effective_message, languages.tl(update.effective_message, "You can do this command in groups, not PM"))
                return ""
            chat = update.effective_chat
            chat_id = update.effective_chat.id
            chat_name = update.effective_message.chat.title

        text = build_curr_disabled(chat.id)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)


    def __stats__():
        return languages.tl(OWNER_ID, "{} disabled items, across {} chats.").format(sql.num_disabled(), sql.num_chats())


    def __import_data__(chat_id, data):
        disabled = data.get('disabled', {})
        for disable_cmd in disabled:
            sql.disable_command(chat_id, disable_cmd)


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        return build_curr_disabled(chat_id)


    __mod_name__ = "Command disabling"

    __help__ = "disable_help"

    DISABLE_HANDLER = CommandHandler("disable", disable, pass_args=True)#, filters=Filters.group)
    ENABLE_HANDLER = CommandHandler("enable", enable, pass_args=True)#, filters=Filters.group)
    COMMANDS_HANDLER = CommandHandler(["cmds", "disabled"], commands)#, filters=Filters.group)
    TOGGLE_HANDLER = CommandHandler("listcmds", list_cmds)#, filters=Filters.group)
    DISABLEDEL_HANDLER = CommandHandler("disabledel", disable_del)

    dispatcher.add_handler(DISABLE_HANDLER)
    dispatcher.add_handler(ENABLE_HANDLER)
    dispatcher.add_handler(COMMANDS_HANDLER)
    dispatcher.add_handler(TOGGLE_HANDLER)
    dispatcher.add_handler(DISABLEDEL_HANDLER)

else:
    DisableAbleCommandHandler = CommandHandler
    DisableAbleRegexHandler = RegexHandler
