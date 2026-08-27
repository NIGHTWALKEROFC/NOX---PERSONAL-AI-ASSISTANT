from logging_setup import setup_logging
logger = setup_logging()

import uvicorn
import config

if __name__ == "__main__":
    logger.info("Starting NOX Brain Server on %s:%s", config.HOST, config.PORT)
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
