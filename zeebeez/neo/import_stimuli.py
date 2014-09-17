import csv
import re
from neosound.sound import *


def import_stimuli_from_protocol_file(protocol_file, output_file, columns=['number',
                                                                           'original_wavefile',
                                                                           'tdt_wavefile',
                                                                           'stim_class',
                                                                           'type',
                                                                           'source',
                                                                           'source_sex',
                                                                           'parameters']):

    # Create the sound manager to store data in h5 file
    sm = SoundManager(HDF5Store, output_file)

    with open(protocol_file, "r") as f:
        creader = csv.reader(f, delimiter="\t")
        for row in creader:
            print("Creating sound object from row %s" % row)
            create_stimulus(columns, row, sm)


def create_stimulus(params, values, manager):

    def process_unused(val):

        if (type(val) is str) and (val.lower() in ["na", "unused"]):
            return "none"
        return val

    def to_float(val):

        try:
            val = float(val)
        except (ValueError, TypeError):
            pass
        return val

    def process_parameters():

        if annotations["parameters"] is not None:
            parameters = re.findall("(\w+)\s*=\s*(\w+)", annotations["parameters"])
            parameters = dict([(kk, process_unused(vv)) for (kk, vv) in parameters])
            annotations.update(parameters)

    params = [ss.lower() for ss in params]
    values = [to_float(process_unused(ss)) for ss in values]

    annotations = dict(zip(params, values))

    if len(values) > len(params):
        annotations["additional_parameters"] = values[len(params):]

    if "parameters" in params:
        process_parameters()

    sound = Sound(annotations["tdt_wavefile"], manager=manager)
    sound.annotate(**annotations)
    print("Added Sound object with id %d" % sound.id)
    print("\tAnnotations include: %s" % ", ".join(sound.annotations.keys()))



