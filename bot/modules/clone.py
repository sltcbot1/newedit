from random import SystemRandom
from string import ascii_letters, digits
from telegram.ext import CommandHandler
from threading import Thread
from time import sleep

from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage, sendFile, sendMarkup
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, STOP_DUPLICATE, download_dict, download_dict_lock, Interval,CLONE_LIMIT
from bot.helper.ext_utils.bot_utils import is_gdrive_link, new_thread, is_gdtot_link, get_readable_file_size
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

def _clone(message, bot):
    try:
        buttons = ButtonMaker()
        TITLE_NAME = "Join Channel"
        CHANNEL_USERNAME = "SLTCUpdates"
        uname = message.from_user.mention_html(message.from_user.first_name)
        user = bot.get_chat_member(-1001691739650, message.from_user.id)
        if user.status not in ['member', 'creator', 'administrator']:
            buttons.buildbutton(f"{TITLE_NAME}", f"https://t.me/{CHANNEL_USERNAME}")
            reply_markup = buttons.build_menu(1)
            return sendMarkup(f"<b>Hey <i><u>{uname}️</u></i>,\n\nFirst join our updates channel</b>", bot, message, reply_markup)
    except Exception as e:
        LOGGER.info(str(e))
    args = message.text.split()
    reply_to = message.reply_to_message
    link = ''
    multi = 0
    if len(args) > 1:
        link = args[1].strip()
        if link.strip().isdigit():
            multi = int(link)
            link = ''
        elif message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
        try:
            tag1 = message.from_user.mention_html(message.from_user.first_name)
            text1 = message.text
            s1 = text1.split(' ', maxsplit=1)
            s2 = s1[0].split('/', maxsplit=1)
            msg = f"<b>User <i>{tag1}</i> sent:</b>\n<code>{link}</code>\n"
            msg += f"<b>With Command:</b>\n<i>{s2[1]}</i>"
            sendMessage(msg, bot, message)
        except:
            pass
    if reply_to:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
        try:
            tag1 = reply_to.from_user.mention_html(reply_to.from_user.first_name)
            text2 = message.text
            s3 = text2.split('/', maxsplit=1)
            msg = f"<b>User <i>{tag1}</i> sent:</b>\n<code>{link}</code>\n"
            msg += f"<b>With Command:</b>\n<i>{s3[1]}</i>"
            sendMessage(msg, bot, message)
        except:
            pass
    is_gdtot = is_gdtot_link(link)
    if is_gdtot:
        try:
            msg = sendMessage(f"Processing: <code>{link}</code>", bot, message)
            link = gdtot(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            return sendMessage(str(e), bot, message)
    if is_gdrive_link(link):
        gd = GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            return sendMessage(res, bot, message)
        if STOP_DUPLICATE:
            LOGGER.info('Checking File/Folder if already in Drive...')
            cap, f_name = gd.drive_list(name, True, True)
            if cap:
                cap = f"File/Folder is already available in Drive. Here are the search results:\n\n{cap}"
                sendFile(bot, message, f_name, cap)
                return
        if CLONE_LIMIT is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > CLONE_LIMIT * 1024 ** 3:
                msg2 = f'Failed, Clone limit is {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}.'
                return sendMessage(msg2, bot, message)
        if multi > 1:
            sleep(4)
            nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
            cmsg = message.text.split()
            cmsg[1] = f"{multi - 1}"
            nextmsg = sendMessage(" ".join(cmsg), bot, nextmsg)
            nextmsg.from_user.id = message.from_user.id
            sleep(4)
            Thread(target=_clone, args=(nextmsg, bot)).start()
        if files <= 20:
            msg = sendMessage(f"Cloning: <code>{link}</code>", bot, message)
            result, button = gd.clone(link)
            deleteMessage(bot, msg)
        else:
            drive = GoogleDriveHelper(name)
            gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
            clone_status = CloneStatus(drive, size, message, gid)
            with download_dict_lock:
                download_dict[message.message_id] = clone_status
            sendStatusMessage(message, bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        cc = f'\n\n<b>➩👤 cc: </b>{tag}'
        if button in ["cancelled", ""]:
            sendMessage(f"{tag} {result}", bot, message)
        else:
            sendMarkup(result + cc, bot, message, button)
            LOGGER.info(f'Cloning Done: {name}')
    else:
        sendMessage("Send Gdrive link along with command or by replying to the link by command\n\n<b>Multi links only by replying to first link/file:</b>\n<code>/cmd</code> 10(number of links/files)", bot, message)

@new_thread
def cloneNode(update, context):
    _clone(update.message, context.bot)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
