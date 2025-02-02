# Copyright (C) 2015-2022 Regents of the University of California
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Accelerator (i.e. GPU) utilities for Toil"""

import subprocess

from typing import Dict, List, Optional, Set
from xml.dom import minidom

from toil.job import AcceleratorRequirement
from toil.lib.memoize import memoize

@memoize
def have_working_nvidia_smi() -> bool:
    """
    Return True if the nvidia-smi binary, from nvidia's CUDA userspace
    utilities, is installed and can be run successfully.

    TODO: This isn't quite the same as the check that cwltool uses to decide if
    it can fulfill a CUDARequirement.
    """
    try:
        subprocess.check_call(['nvidia-smi'])
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return True

@memoize
def have_working_nvidia_docker_runtime() -> bool:
    """
    Return True if Docker exists and can handle an "nvidia" runtime and the "--gpus" option.
    """
    try:
        # The runtime injects nvidia-smi; it doesn't seem to have to be in the image we use here
        subprocess.check_call(['docker', 'run', '--rm', '--runtime', 'nvidia', '--gpus', 'all', 'ubuntu:20.04', 'nvidia-smi'])
    except subprocess.CalledProcessError:
        return False
    return True

@memoize
def count_nvidia_gpus() -> int:
    """
    Return the number of nvidia GPUs seen by nvidia-smi, or 0 if it is not working.
    """

    # I don't have nvidia-smi, but cwltool knows how to do this, so we do what
    # they do:
    # <https://github.com/common-workflow-language/cwltool/blob/6f29c59fb1b5426ef6f2891605e8fa2d08f1a8da/cwltool/cuda.py>
    # Some example output is here: <https://gist.github.com/loretoparisi/2620b777562c2dfd50d6b618b5f20867>
    try:
        return int(minidom.parseString(
            subprocess.check_output(["nvidia-smi", "-q", "-x"])
        ).getElementsByTagName("attached_gpus")[0].firstChild.data)
    except (FileNotFoundError, subprocess.CalledProcessError, IndexError, ValueError):
        return 0

    # TODO: Parse each gpu > product_name > text content and convert to some
    # kind of "model" that agrees with e.g. Kubernetes naming.


@memoize
def get_individual_local_accelerators() -> List[AcceleratorRequirement]:
    """
    Determine all the local accelerators available. Report each with count 1,
    in the order of the number that can be used to assign them.

    TODO: How will numbers work with multiple types of accelerator? We need an
    accelerator assignment API.
    """

    # For now we only know abput nvidia GPUs
    return [{'kind': 'gpu', 'brand': 'nvidia', 'api': 'cuda', 'count': 1} for _ in range(count_nvidia_gpus())]

def get_restrictive_environment_for_local_accelerators(accelerator_numbers : Set[int]) -> Dict[str, str]:
    """
    Get environment variables which can be applied to a process to restrict it
    to using only the given accelerator numbers.

    The numbers are in the space of accelerators returned by
    get_individual_local_accelerators().
    """

    # Since we only know about nvidia GPUs right now, we can just say our
    # accelerator numbering space is the same as nvidia's GPU numbering space.
    return {'CUDA_VISIBLE_DEVICES': ','.join((str(i) for i in accelerator_numbers))}


