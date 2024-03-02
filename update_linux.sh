# Globals.

t_dir_conda="$(pwd)/miniconda"

log() {
    echo -e "\n\n$1\n\n"
}

stop_w_err() {
    echo -e "\n\n$1\n\n"
    exit 1
}

# Ensure git and curl are installed.

for dep in git curl; do
    if ! which $dep >/dev/null 2>&1; then
        stop_w_err "You need to install $dep first!"
    fi
done

rm -rf $t_dir_conda

git fetch --all

if [ $? -ne 0 ]; then
    stop_w_err "Update failed!"
fi

git reset --hard origin/main

if [ $? -ne 0 ]; then
    stop_w_err "Update failed!"
fi

git pull --force

if [ $? -ne 0 ]; then
    stop_w_err "Update failed!"
fi

log "Update done! Run start.sh to complete setup."
