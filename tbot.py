from telebot import TeleBot, logger as tblogger, types as tbtypes, apihelper
import logging
import time
import sys
from db import *
import traceback

TOKEN = ''

bot = TeleBot(token=TOKEN)
#tblogger.setLevel(logging.DEBUG)

user_edit_sticker = {}
list_of_stickers_showed_to_user = {}

@bot.chosen_inline_handler(func=lambda chosen_inline_result: True)
def chosen_handler(chosen_inline_result):
    try:
        sticker = list_of_stickers_showed_to_user[chosen_inline_result.from_user.id][int(chosen_inline_result.result_id)]
        use_sticker(sticker, chosen_inline_result.from_user.id)
        db_save()
    except Exception:
        pass

@bot.message_handler(commands=['kwlist'])
def kwlist_cmd_handler(message):
    lst = '\n'.join([kw + ' - ' + str(cnt) for kw, cnt in get_kw_dict_count()[0:100]])
    bot.send_message(message.from_user.id, 'Список тегов:\n\n' + lst)

@bot.message_handler(commands=['stop_bot'])
def stop_cmd_handler(message):
    bot.send_message(message.from_user.id, 'Бот остановлен')
    sys.exit(0)

@bot.inline_handler(lambda query: len(query.query) > 1)
def inline_query(inline_query):
    #print(f'Req: {inline_query.query}')
    log_inline_query(inline_query.from_user.id, inline_query.query)
    stickers_list = get_stickers_by_word(inline_query.query.lower())
    stickers_list2 = get_stickers_by_word(inline_query.query.lower(), fuzzy=False)
    if len(stickers_list2):
        if stickers_list2[-1] in stickers_list:
            stickers_list.remove(stickers_list2[-1])
        stickers_list.insert(min(len(stickers_list), 3), stickers_list2[-1])
    stickers = []
    for i,s in enumerate(stickers_list[:50]):
        stickers.append(tbtypes.InlineQueryResultCachedSticker(i, s))
    list_of_stickers_showed_to_user[inline_query.from_user.id] = stickers_list[:50]
    #print(f'Res: {stickers}')
    try:
        bot.answer_inline_query(inline_query.id, stickers, cache_time=5)
    except apihelper.ApiException:
        log_errors(traceback.format_exc())

@bot.inline_handler(lambda query: len(query.query) == 0)
def inline_empty_query(inline_query):
    rnd_stickers = get_random_stickers()
    stickers = [tbtypes.InlineQueryResultCachedSticker(i, s) for i,s in enumerate(rnd_stickers)]
    list_of_stickers_showed_to_user[inline_query.from_user.id] = rnd_stickers
    try:
        bot.answer_inline_query(inline_query.id, stickers, cache_time=1)
    except apihelper.ApiException:
        log_errors(traceback.format_exc())

@bot.message_handler(content_types=['sticker'])
def sticker_received(message):
    if message.from_user.id != 194573162:
        bot.send_message(message.from_user.id, 'Sorry, but stickers editing available only for admin')
        return
    user_edit_sticker[message.from_user.id] = message.sticker.file_id
    if add_sticker(message.sticker.file_id, [], set_name=message.sticker.set_name):
        bot.send_message(message.from_user.id, 'Стикер добавлен, введите список тегов к нему через пробел')
    else:
        info = get_sticker_info(message.sticker.file_id)
        keywords, last_send, send_times = info['keywords'], info['last_using'], info['send_times']
        bot.send_message(message.from_user.id, f'Стикер {message.sticker.file_id}\n\nИспользований: {send_times}\nПоследний раз был отправлен: {last_send}\nСписок тегов: {", ".join(keywords)}\n\nЧтобы добавить новые теги просто напишите их')#, parse_mode="Markdown")

@bot.message_handler(content_types=['text'])
def tags_received(message):
    if message.from_user.id != 194573162:
        bot.send_message(message.from_user.id, 'Sorry, but text commands available only for admin')
        return
    if message.from_user.id not in user_edit_sticker:
        return
    tags = message.text.lower().replace(',', '').replace('_','').split(' ')
    add_keywords(user_edit_sticker[message.from_user.id], tags)
    bot.send_message(message.from_user.id, f'К стикеру *{user_edit_sticker[message.from_user.id]}* добавлены теги:\n _{", ".join(tags)}_', parse_mode="Markdown")
    db_save()



def main_loop():
    bot.polling(True)
    while 1:
        time.sleep(3)


if __name__ == '__main__':
    try:
        db_load()
        main_loop()
    except KeyboardInterrupt:
        print('\nExiting by user request.\n')
        sys.exit(0)