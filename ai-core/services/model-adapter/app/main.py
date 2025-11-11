import os
import uvicorn
from controllers.api import create_app


app = create_app()


if __name__ == "__main__":
	port = int(os.getenv("PORT", "8000"))
	uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

 