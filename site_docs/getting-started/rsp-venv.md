# Rubin Science Platform Venv

This page documents the recommended clean install path for running INJECT notebooks on the Rubin Science Platform (RSP) with a project-specific Jupyter kernel.

RSP already provides Rubin Science Pipelines in `/opt/lsst/software/stack`. The INJECT virtual environment does not install Rubin Butler or `lsst_distrib`; it uses the RSP stack and installs only INJECT plus its Python dependencies.

Use this venv path when you want:

- a named `Python (inject-rsp)` notebook kernel
- an editable install from your INJECT checkout
- a clean separation between INJECT dependencies and the standard RSP kernel

If you only need the standard Rubin stack plus an editable INJECT checkout, a venv is optional. See [Installation](installation.md) for the simpler standard-kernel path.

## Clean Out An Old Install

Open an RSP JupyterLab terminal with `File` -> `New` -> `Terminal`.

Remove the old custom kernel:

```bash
jupyter kernelspec remove -f inject-rsp
```

Make sure no notebook kernel is still running from the old venv:

```bash
ps -u "$USER" -f | grep -E 'inject-rsp|ipykernel|jupyter|python' | grep -v grep
```

If you see a process whose command starts with `~/venvs/inject-rsp/bin/python`, stop that process before deleting the venv:

```bash
kill PID
```

Replace `PID` with the process ID shown in the second column of the `ps` output. If it does not stop, use:

```bash
kill -9 PID
```

Then remove the old venv:

```bash
rm -rf ~/venvs/inject-rsp
```

Confirm it is gone:

```bash
ls -ld ~/venvs/inject-rsp 2>/dev/null || echo "old inject-rsp venv is gone"
```

If `rm -rf` reports `Directory not empty`, the most common cause is a still-running notebook kernel using files inside the venv. Stop the matching `~/venvs/inject-rsp/bin/python` process and rerun the remove command. If the directory still cannot be removed, restart your RSP server from the Hub control panel and remove it from a fresh terminal.

## Install Fresh

Go to your INJECT checkout on RSP:

```bash
cd ~/WORK/INJECT
```

If your checkout is somewhere else, find it with:

```bash
find ~ -maxdepth 4 -type d -name INJECT 2>/dev/null
```

Update the checkout if it is connected to Git:

```bash
git pull
```

Run the setup script:

```bash
bash scripts/setup_rsp_env.sh
```

The script performs these steps:

- loads `/opt/lsst/software/stack/loadLSST.bash`
- runs `setup lsst_distrib`
- creates `~/venvs/inject-rsp` with `--system-site-packages`
- installs INJECT in editable mode with the `jupyter` extra
- writes `~/venvs/inject-rsp/bin/activate-rsp`
- registers the `Python (inject-rsp)` Jupyter kernel
- verifies that both Rubin Butler and INJECT import from the kernel environment

Expected success output includes:

```text
[inject-setup] Butler import OK
[inject-setup] INJECT import OK from .../INJECT/inject/__init__.py
[inject-setup] Butler import OK inside kernel environment
[inject-setup] Kernel imports INJECT from .../INJECT/inject/__init__.py
[inject-setup] RSP setup complete.
```

## Terminal Use

For later RSP terminal sessions, activate both the Rubin stack and the INJECT venv with:

```bash
source ~/venvs/inject-rsp/bin/activate-rsp
```

Verify the terminal environment:

```bash
python -c "from lsst.daf.butler import Butler; print('Butler OK')"
python -c "import inject; print('INJECT OK:', inject.__file__)"
python -c "from inject import InjectionConfig, InjectionPipeline; print('Pipeline OK')"
```

The INJECT path should point at your RSP checkout, for example:

```text
/home/snair63/WORK/INJECT/inject/__init__.py
```

## Notebook Use

In RSP JupyterLab:

1. Open a notebook from the same INJECT checkout used during installation.
2. Select `Kernel` -> `Change Kernel` -> `Python (inject-rsp)`.
3. Select `Kernel` -> `Restart Kernel and Clear Outputs`.
4. Run the notebook from the top.

Start with the smallest Butler validation notebook:

```text
notebooks/dp2_early_release_injection_smoke_test.ipynb
```

Then move to the larger workflow notebooks:

```text
notebooks/simple_rubin_mci_demo.ipynb
notebooks/simple_batch_injection_demo.ipynb
notebooks/simple_multiband_injection_demo.ipynb
```

## Troubleshooting

!!! warning "`ModuleNotFoundError: No module named 'lsst.daf'`"
    The active notebook kernel has not loaded `lsst_distrib`. Switch to `Python (inject-rsp)` and restart the kernel. If the kernel is missing or stale, rerun `bash scripts/setup_rsp_env.sh` from the INJECT checkout.

!!! warning "`RUBIN_EUPS_PATH: unbound variable` during setup"
    Update your checkout and rerun `bash scripts/setup_rsp_env.sh`. The setup script temporarily disables Bash nounset while loading Rubin stack startup scripts because those scripts may reference variables before defining them.

!!! warning "`rm -rf ~/venvs/inject-rsp` says `Directory not empty`"
    A notebook kernel is probably still running from that venv. Find it with `ps -u "$USER" -f | grep -E 'inject-rsp|ipykernel' | grep -v grep`, stop the matching process, and remove the venv again.

!!! warning "The notebook imports the wrong `inject` package"
    Reopen the notebook from the checkout used for installation, select `Python (inject-rsp)`, restart the kernel, and rerun from the top. The first code cell in the maintained Rubin notebooks prints the imported INJECT path.