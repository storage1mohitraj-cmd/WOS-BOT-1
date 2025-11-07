import logging
import sys

# mimic the reconfiguration applied in app.py
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    else:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('__test__')
logger.info('[GUILD: DM (DM)] [CHANNEL: DM (1436297420828049450)] [AUTHOR: M𝖆𝖌𝖓𝖚s (850786361572720661)] msg_id=1436357047934517318 attachments=0 Content: hi')
print('done')
