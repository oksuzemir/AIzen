import json
import logging

from .message import *
from .user import *
import time

logger = logging.getLogger()

def talks_to_msgs(messages, room):
    """Converts the talks list into a list of messages, room is the room object"""
    return [talk_to_msg(m, room) for m in messages]


def talk_to_msg(msg, room):
    """msg is one individual json object representing a talk"""

    m = None
    if 'error' in msg:
        if 'reload' in msg:
            m = ErrorMessage(msg['error'], msg['reload'])
        else:
            m = ErrorMessage(msg['error'])

    elif msg['type'] == 'message':
        if 'url' in msg:
            if 'to' in msg:
                # Direct URL message için user kontrolü
                from_user = room.users.get(msg['from']['id'], None)
                to_user = room.users.get(msg['to']['id'], None)
                
                if from_user is None and 'from' in msg:
                    user_data = msg['from']
                    from_user = User(
                        user_data['id'],
                        user_data.get('name', 'misafir'),
                        user_data.get('icon', 'setton'),
                        user_data.get('tripcode', '无'),
                        user_data.get('device', 'Unknown'),
                        user_data.get('admin', False)
                    )
                    room.users[from_user.id] = from_user
                    print(f"⚠️  Unknown user added to room: {from_user.name} (ID: {from_user.id})")
                
                m = DirectURLMessage(msg['id'], msg['time'], Message_Type.dm_url, from_user, to_user, msg['message'], msg['url'])
            else:
                # URL message için user kontrolü
                user_obj = room.users.get(msg['from']['id'], None)
                if user_obj is None and 'from' in msg:
                    user_data = msg['from']
                    user_obj = User(
                        user_data['id'],
                        user_data.get('name', 'misafir'),
                        user_data.get('icon', 'setton'),
                        user_data.get('tripcode', '无'),
                        user_data.get('device', 'Unknown'),
                        user_data.get('admin', False)
                    )
                    room.users[user_obj.id] = user_obj
                    print(f"⚠️  Unknown user added to room: {user_obj.name} (ID: {user_obj.id})")
                
                m = URLMessage(msg['id'], msg['time'], Message_Type.url, user_obj, msg['message'], msg['url'])
        else:
            if 'to' in msg:
                # Direct message için user kontrolü
                from_user = room.users.get(msg['from']['id'], None)
                to_user = room.users.get(msg['to']['id'], None)
                
                if from_user is None and 'from' in msg:
                    user_data = msg['from']
                    from_user = User(
                        user_data['id'],
                        user_data.get('name', 'misafir'),
                        user_data.get('icon', 'setton'),
                        user_data.get('tripcode', '无'),
                        user_data.get('device', 'Unknown'),
                        user_data.get('admin', False)
                    )
                    room.users[from_user.id] = from_user
                    print(f"⚠️  Unknown user added to room: {from_user.name} (ID: {from_user.id})")
                
                m = DirectMessage(msg['id'], msg['time'], Message_Type.dm, from_user, to_user, msg['message'])

            else:
                # User objesini al, yoksa mesajdan oluştur
                user_obj = room.users.get(msg['from']['id'], None)
                if user_obj is None and 'from' in msg:
                    # User room'da değil, mesajdan bilgi al
                    user_data = msg['from']
                    user_obj = User(
                        user_data['id'],
                        user_data.get('name', 'misafir'),
                        user_data.get('icon', 'setton'),
                        user_data.get('tripcode', '无'),
                        user_data.get('device', 'Unknown'),
                        user_data.get('admin', False)
                    )
                    # Room'a ekle
                    room.users[user_obj.id] = user_obj
                    print(f"⚠️  Unknown user added to room: {user_obj.name} (ID: {user_obj.id})")
                
                m = Message(msg['id'], msg['time'], Message_Type.message, user_obj, msg['message'])

    elif msg['type'] == 'music':
        user_obj = room.users.get(msg['from']['id'], None)
        if user_obj is None and 'from' in msg:
            user_data = msg['from']
            user_obj = User(
                user_data['id'],
                user_data.get('name', 'misafir'),
                user_data.get('icon', 'setton'),
                user_data.get('tripcode', '无'),
                user_data.get('device', 'Unknown'),
                user_data.get('admin', False)
            )
            room.users[user_obj.id] = user_obj
            print(f"⚠️  Unknown user added to room: {user_obj.name} (ID: {user_obj.id})")
        
        m = MusicMessage(msg['id'], msg['time'], user_obj, msg['music']['name'],
                        msg['music']['playURL'], msg['music']['shareURL'], msg['music']['playURL'], msg['music']['shareURL'])

    elif msg['type'] == 'me':
        user_obj = room.users.get(msg['from']['id'], None)
        if user_obj is None and 'from' in msg:
            user_data = msg['from']
            user_obj = User(
                user_data['id'],
                user_data.get('name', 'misafir'),
                user_data.get('icon', 'setton'),
                user_data.get('tripcode', '无'),
                user_data.get('device', 'Unknown'),
                user_data.get('admin', False)
            )
            room.users[user_obj.id] = user_obj
            print(f"⚠️  Unknown user added to room: {user_obj.name} (ID: {user_obj.id})")
        
        m = MeMessage(msg['id'], msg['time'], user_obj, msg['content'])

    elif msg['type'] == 'new-host':
        m = NewHostMessage(msg['id'], msg['time'], room.users.get(msg['user']['id'], None))

    elif msg['type'] == 'leave':
        m = LeaveMessage(msg['id'], msg['time'], room.users.get(msg['user']['id'], None))

    elif msg['type'] == 'join':
        # Name boş gelirse default değer ata
        user_name = msg['user'].get('name', '')
        if not user_name or (isinstance(user_name, str) and not user_name.strip()):
            user_name = "misafir"
        
        m = JoinMessage(msg['id'], msg['time'], User(msg['user']['id'], user_name, msg['user']['icon'],
                                                msg['user']['tripcode'] if 'tripcode' in msg['user'] else "无",msg['user']['device'],
                                                True if 'admin' in msg['user'].keys() and msg['user']['admin'] else False))

    elif msg['type'] == 'async-response':
        m = AsyncResponse(msg['id'], msg['time'], msg['secret'],room.users.get(msg['to']['id'], None), msg['message'],
                          msg['title'], msg['level'], None)

    elif msg['type'] == 'kick':
        m = KickMessage(msg['id'], msg['time'],room.users.get(msg['to']['id'], None), msg['message'])

    elif msg['type'] == 'ban':
        target_id = msg['to']['id']
        m = BanMessage(msg['id'], msg['time'], room.users[target_id] if target_id in room.users else target_id, msg['message'])

    elif msg['type'] == 'unban':
        m = UnbanMessage(msg['id'], msg['time'], BannedUserInfo(msg['to']['id'], msg['to']['name'],
                                                msg['to']['tripcode'] if 'tripcode' in msg['to'] else None, msg['to']['icon']), msg['message'])

    elif msg['type'] == 'system':
        m = SystemMessage(msg['id'], msg['time'], msg['message'])

    elif msg['type'] == 'room-profile':
        m = RoomProfileMessage(msg['id'], msg['time'], room.users[room.host_id])

    elif msg['type'] == 'new-description':
        m = NewDescMessage(msg['id'], msg['time'], room.users.get(msg['from']['id'], None), msg['description'])

    elif msg['type'] == 'user-profile':
        pass
    elif msg['type'] == 'knock':
        # Kapı çalma mesajı - görmezden gel
        pass
    else:
        logger.warning(f'未知消息类型: {msg["type"]}')
        logger.warning(msg)
    return m
