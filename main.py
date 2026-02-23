import asyncio
import copy
import os
import sys
import traceback
import networking
import importlib
import concurrent.futures
from modules import module
import logging
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

defaultConfig = {
  'name': 'AIzen',
  'tc': 'None',
  'avatar': 'setton',
  'agent': 'Bot',
  'roomID': '6JjYq34S35',
  'throttle': 1.5,
  'mods' : ['AIzen']
}

config = copy.deepcopy(defaultConfig)
if not os.path.exists('config.txt'):
    with open('config.txt', 'w') as f:
        for key, value in config.items():
            if key != 'mods':
                f.write(f"{key} = {value}\n")
            else:
                f.write(f"{key} = {', '.join(value)}\n")

with open('config.txt', 'r', encoding='utf8') as f:
    for line in f:
        line = line.strip()
        if line.startswith('#') or not line:
            continue
        key, value = [x.strip() for x in line.split('=')]
        if(key=='mods'):
            value = [x.strip() for x in value.split(',')]
        elif(key=='throttle'):
            value = float(value)
        config[key] = value

print('配置：')
for k, v in config.items():
    print(f'   {k}: {v}')
print()

modules = {}
mods_dir = 'modules'
logger = logging.getLogger(__name__)


def load_module(name, bot):
    importlib.invalidate_caches()
    if name in modules.keys():
        logger.error(f'模块【{name}】已存在')
        return False
    try:
        mod = importlib.import_module(mods_dir + '.' + name)
    except ModuleNotFoundError as e:
        logger.error(f'未找到模块【{name}】: {e}')
        return False
    except Exception as e:
        logger.error(f'加载模块【{name}】时出错: {e}')
        return False

    try:
        cls = getattr(mod, name)
    except AttributeError:
        logger.error('模块必须有一个与自身同名的顶级类')
        return False

    if not issubclass(cls, module.Module):
        logger.error('模块的顶级类必须继承自 module.Module')
        return False
    logger.info('\033[1;36m' + f'加载模块【{name}】' + '\033[0m')
    modules[name] = cls(bot)

def unload_module(name):
    try:
        modules[name].unload()
        modules[name].cancel_all_event_loops()

        del modules[name]
        del sys.modules[mods_dir + '.' + name]
        del sys.modules[mods_dir + '.' + name + '.' + name]
        for mod in list(sys.modules.keys()):
            if mod.startswith(mods_dir + '.' + name ):
                del sys.modules[mod]

    except KeyError:
        logger.error(f'模块【{name}】未加载')
    except Exception:
        logger.error(traceback.format_exc())

executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
async def handler(msg):
    try:
        for k, v in modules.items():
            # Her modülü paralel çalıştır ama exception'ları yakala
            try:
                loop.run_in_executor(executor, v.handler, msg)
            except Exception as e:
                logger.error(f"❌ Modül [{k}] mesaj işlerken hata: {str(e)[:100]}")
    except Exception as e:
        logger.error(f"❌ Handler genel hatası: {str(e)[:100]}")


if __name__ == '__main__':
    logger.info('程序启动')
    
    # Windows için event loop policy ayarla
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    bot = networking.Connection(config['name'], config['tc'], config['avatar'], config['roomID'], config['agent'], config['throttle'], handler, loop)
    for mod in config['mods']:
        load_module(mod, bot)

    bot.start()
