#!/usr/bin/env python3

"""Set up Qiime 2 on Google colab.

Do not use this on o local machine, especially not as an admin!
"""

import os
import sys
import shutil
from subprocess import Popen, PIPE, run

r = Popen(["pip", "install", "rich"])
r.wait()
from rich.console import Console  # noqa
con = Console()

PREFIX = "/usr/local/miniforge3/"

has_conda = "conda version" in os.popen("%s/bin/conda info" % PREFIX).read()
qiime_installed = os.path.exists(os.path.join(PREFIX, "envs", "qiime2", "bin", "qiime"))
qiime_active = "QIIME 2 release:" in os.popen("qiime info").read()


MINICONDA_PATH = (
    "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
)

QIIME_YAML_TEMPLATE = (
    "https://data.qiime2.org/distro/amplicon/qiime2-amplicon-{version}-py{python}-linux-conda.yml"
)

if len(sys.argv) == 2:
    version = sys.argv[1]
else:
    version = "2025.4"

qiime_ver = tuple(int(v) for v in version.split("."))

if qiime_ver < (2021, 4):
    pyver = "36"
elif qiime_ver < (2024, 5):
    pyver = "38"
elif qiime_ver < (2024, 10):
    pyver = "39"
else:
  pyver = "310"

CONDA = "mamba"
CONDA_ARGS = ["-q"] if CONDA == "conda" else ["-y"]

if tuple(float(v) for v in version.split(".")) < (2023, 9):
    QIIME_YAML_TEMPLATE = (
        "https://data.qiime2.org/distro/core/qiime2-{version}-py{python}-linux-conda.yml"
    )

QIIME_YAML_URL = QIIME_YAML_TEMPLATE.format(version=version, python=pyver)
QIIME_YAML = os.path.basename(QIIME_YAML_URL)


def cleanup():
    """Remove downloaded files."""
    if os.path.exists(os.path.basename(MINICONDA_PATH)):
        os.remove(os.path.basename(MINICONDA_PATH))
    if os.path.exists(QIIME_YAML):
        os.remove(QIIME_YAML)
    if os.path.exists("/content/sample_data"):
        shutil.rmtree("/content/sample_data")
    con.log(":broom: Cleaned up unneeded files.")


def run_and_check(args, check, message, failure, success, console=con):
    """Run a command and check that it worked."""
    console.log(message)
    r = Popen(args, env=os.environ, stdout=PIPE, stderr=PIPE,
              universal_newlines=True)
    o, e = r.communicate()
    out = o + e
    if r.returncode == 0 and check in out:
        console.log("[blue]%s[/blue]" % success)
    else:
        console.log("[red]%s[/red]" % failure, out)
        open("logs.txt", "w").write(out)
        cleanup()
        sys.exit(1)

def run_in_env(cmd, env, console=con):
    """Activate a conda environment in colab."""
    conda_profile = os.path.join(PREFIX, "etc", "profile.d", "conda.sh")
    console.log(f":snake: Activating the {env} environment.")

    full = f". {conda_profile} && conda activate {env} && {cmd}"
    return run(
        full,
        shell=True,
        executable="/bin/bash",
        capture_output=True,
        text=True
    )

def mock_qiime2(console=con):
    con.log(":penguin: Setting up the Qiime2 command...")
    conda_profile = os.path.join(PREFIX, "etc", "profile.d", "conda.sh")
    with open("/usr/local/bin/qiime", "w") as mocky:
        mocky.write("#!/usr/bin/env bash")
        mocky.write(f'\n\n. {conda_profile} && conda activate qiime2 && qiime "$@"\n')
    run("chmod +x /usr/local/bin/qiime", shell=True, executable="/bin/bash")
    con.log(":penguin: Done.")

if __name__ == "__main__":
    if not has_conda:
        run_and_check(
            ["wget", MINICONDA_PATH],
            "saved",
            ":snake: Downloading miniforge...",
            "failed downloading miniforge :sob:",
            ":snake: Done."
        )

        run_and_check(
            ["bash", os.path.basename(MINICONDA_PATH), "-bfp", PREFIX],
            "installation finished.",
            ":snake: Installing miniforge...",
            "could not install miniforge :sob:",
            ":snake: Installed miniforge to `/usr/local`."
        )
    else:
        con.log(":snake: Miniforge is already installed. Skipped.")

    if not qiime_installed:
        run_and_check(
            ["wget", QIIME_YAML_URL],
            "saved",
            ":mag: Downloading Qiime 2 package list...",
            "could not download package list :sob:",
            ":mag: Done."
        )

        if CONDA == "mamba":
            CONDA_ARGS.append("-y")

        run_and_check(
            [PREFIX + "bin/" + CONDA, "env", "create", *CONDA_ARGS, "-n", "qiime2", "--file", QIIME_YAML],
            "Verifying transaction: ...working... done" if CONDA == "conda" else "Transaction finished",
            f":mag: Installing Qiime 2 ({version}). This may take a little bit.\n :clock1:",
            "could not install Qiime 2 :sob:",
            ":mag: Done."
        )

        mock_qiime2()

        con.log(":evergreen_tree: Installing empress...")
        rc = run_in_env(
            "pip install --verbose Cython && pip install iow==1.0.7 empress",
            "qiime2"
        )
        if rc.returncode == 0:
            con.log(":evergreen_tree: Done.")
        else:
            con.log("could not install Empress :sob:")
    else:
        con.log(":mag: Qiime 2 is already installed. Skipped.")
        if not qiime_active:
            mock_qiime2()

    run_and_check(
        ["qiime", "info"],
        "QIIME 2 release:",
        ":bar_chart: Checking that Qiime 2 command line works...",
        "Qiime 2 command line does not seem to work :sob:",
        ":bar_chart: Qiime 2 command line looks good :tada:"
    )

    cleanup()

    con.log("[green]Everything is A-OK. "
            "You can start using Qiime 2 now :thumbs_up:[/green]")