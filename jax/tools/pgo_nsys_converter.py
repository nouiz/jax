# Copyright 2024 The JAX Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import csv
import re
import sys
import argparse
import os
import shutil
import subprocess

print("Script to convert NVIDIA Nsys Profiles to the .pbtxt format. This format is readable by XLA's Profile Guided Latency Estimator. Usage: pgo_nsys_converter.py --profile_path <path the nsys profile> --pgle_output_path <path to output .pbtxt>")

nsys_path = shutil.which("nsys")

parser = argparse.ArgumentParser(description='Tool to convert NVIDIA Nsys Profiles to the .pbtxt format')
parser.add_argument("--profile_path", type=str, help="path to nsys profile")
parser.add_argument("--post_process", help="post process pbtxt to get minimum cost value for each instruction", action="store_true")
parser.add_argument("--pgle_output_path", type=str, help="output directory", default="/opt/paxml/workspace/lhs_pbtxt/temp.pbtxt")

args = parser.parse_args()

pgle_filename = os.path.basename(args.pgle_output_path).partition('.')[0]
pgle_folder = os.path.join(os.path.split(args.pgle_output_path)[0], '')
profile_folder = os.path.join(os.path.split(args.profile_path)[0], '')

stats_command = [nsys_path, "stats", "--force-overwrite", "true", "--force-export", "true", "--report", "nvtxkernsum", f"{args.profile_path}", "-o", f"{args.pgle_output_path}"]

print(f"""
  ******Starting stats command******
  {stats_command}.""")

proc = subprocess.Popen(stats_command, stdout=sys.stdout, stderr=sys.stderr)
proc.wait()

thunk_re = re.compile("hlo_op=(.*)#")
cost_dictionary = dict()
with open(f"{args.pgle_output_path}", 'w', newline='') as protofile:
    with open(f"{pgle_folder}{pgle_filename}.pbtxt_nvtxkernsum.csv", newline='') as csvfile:
      reader = csv.DictReader(csvfile)
      for row in reader:
        name = row['NVTX Range']
        time_ns = float(row['Avg (ns)'])
        m = thunk_re.search(name)
        if m is not None:
          protofile.write(f'costs {{ name: "{m.group(1)}" cost_us: {time_ns / 1000.0} }}\n')

clean_command = f"rm {profile_folder}/*.sqlite; rm {pgle_folder}/*.csv"
subprocess.call(clean_command, shell=True)
