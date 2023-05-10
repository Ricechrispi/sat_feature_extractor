import subprocess
import argparse
import csv
import os
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("feature_runner")

def calc_all_features(instance):

    cmd = ['satzilla/features']
    # '-lp' does not work...
    arguments = ['-base', '-unit', '-sp', '-dia', '-cl', '-ls', '-lobjois', instance]
    cmd.extend(arguments)

    # actually run the satzilla file extractor
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    logger.debug('---------------stdout--------------')
    logger.debug(result.stdout)
    logger.debug('---------------stderr--------------')
    logger.debug(result.stderr)

    lines = result.stdout.split('\n')
    feature_names = lines[-3].split(',')
    feature_values = lines[-2].split(',')

    # add the instance name as an index
    header = ['instance_name']
    values = [os.path.basename(instance)]
    header.extend(feature_names)
    values.extend(feature_values)

    return header, values


# retrieves a given amount of .cnf files from a given folder.
# use amount=-1 for all instances.
def get_instances(instance_folder, amount=-1):
    instances = []
    iteration = 0
    for file in os.listdir(instance_folder):
        filename = os.fsdecode(file)
        if filename.endswith('.cnf'):
            iteration += 1
            if amount != -1 and iteration > amount:
                break
            instances.append(os.path.join(instance_folder, filename))
    return instances


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-instance_folder', dest='instance_folder', type=str, default='instances')
    parser.add_argument('-combined_file', dest='combined_file', type=str, default='features.csv')
    parser.add_argument('-max_workers', dest='max_workers', type=int, default=10)
    args = parser.parse_args()
    return args


def main():
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    logging.debug(f'args: {args}')

    # get a list of all instances in the chosen folder
    instances = get_instances(instance_folder=args.instance_folder)

    # for each instance, calculate all features (in parallel threads)
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        result = executor.map(calc_all_features, instances)
        executor.shutdown(wait=True)

    # convert the result into a list with a single header,
    #   as each thread calculates its own header.
    feature_list = []
    common_header = None
    for header, values in result:
        feature_list.append(values)
        if common_header is None:
            # the header used for the final file
            common_header = header
        else:
            # defensive programming, make sure that all threads give us the same features
            assert common_header == header

    # finally store this into a single .csv file
    with open(args.combined_file, 'w') as c_file:
        csv_writer = csv.writer(c_file, delimiter=',')

        lines = [common_header]
        lines.extend(feature_list)
        # logging.debug(f'lines for combined file: {lines}') # warning: prints A LOT
        csv_writer.writerows(lines)


if __name__ == "__main__":
    main()
