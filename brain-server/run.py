import logging
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

import uvicorn
import config

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
