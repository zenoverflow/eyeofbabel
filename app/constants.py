import os
import app.util.mode as appmode

KEY_FILE_RECAPTURE = os.path.join(appmode.exec_path(), ".recapture")

KEY_FILE_LOCK_MAIN = os.path.join(appmode.exec_path(), ".applock")

MSG_DT_LOADING = "++ Loading..."

MSG_DT_LOADED = ">> Loaded!"

MSG_DT_NOT_LOADED = "-- Not running."
