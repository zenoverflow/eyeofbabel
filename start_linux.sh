# Globals.

t_conda_dist="Miniconda3-latest-Linux-x86_64.sh"
t_dir_conda="$(pwd)/miniconda"
t_hook="$(pwd)/miniconda/etc/profile.d/conda.sh"
t_env="eyeofbabel"

log() {
    echo -e "\n\n$1\n\n"
}

stop_w_err() {
    echo -e "\n\n$1\n\n"
    rm -rf $t_dir_conda
    exit 1
}

# Ensure git and curl are installed.

for dep in git curl; do
    if ! which $dep >/dev/null 2>&1; then
        stop_w_err "You need to install $dep first!"
    fi
done

# Ensure miniconda is set up.

if [ ! -d $t_dir_conda ] || [ ! -f $t_hook ]; then
    # Dir cleanup and download.
    log "Downloading miniconda..."
    curl -O https://repo.anaconda.com/miniconda/$t_conda_dist

    if [ $? -ne 0 ]; then
        stop_w_err "Failed to download miniconda!"
    fi

    # Installation.
    rm -rf $t_dir_conda
    bash $t_conda_dist -b -p $t_dir_conda
    rm $t_conda_dist
    # Recheck.
    if [ ! -d $t_dir_conda ] || [ ! -f $t_hook ]; then
        stop_w_err "Failed to install miniconda!"
    fi
fi

# Conda shell hook (so we can call conda).

. $t_hook

if ! which conda >/dev/null 2>&1; then
    stop_w_err "Failed to hook into conda!"
fi

# Ensure a conda environment is set up.

if $(conda env list | grep -q "^$t_env"); then
    log "Using existing conda env."
else
    log "Creating new conda env. This will take a while..."

    conda create --name $t_env python=3.11.7 --yes

    if $(conda env list | grep -q "^$t_env"); then
        log "Created a fresh conda env."
    else
        stop_w_err "Failed to create a fresh conda env!"
    fi

    conda install -n $t_env pip --yes

    if [ $? -ne 0 ]; then
        stop_w_err "Failed to install pip!"
    fi

    conda install -n $t_env --yes \
        'pytorch==2.1.2' 'torchvision==0.16.2' 'torchaudio==2.1.2' cpuonly -c pytorch

    if [ $? -ne 0 ]; then
        stop_w_err "Failed to install pytorch!"
    fi

    conda run -n $t_env --no-capture-output bash -c \
        "pip install -r requirements.txt"

    if [ $? -ne 0 ]; then
        stop_w_err "Failed to install dependencies!"
    fi
fi

# Run the app.

conda run -n $t_env --no-capture-output bash -c "python3 app.py $*"
