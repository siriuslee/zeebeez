import re
import quantities as pq
import csv
import numpy as np
from neo import *
from neosound.sound_manager import SoundManager, HDF5Store


class Stimulus(object):

    def __init__(self, params, values):

        params = [ss.lower() for ss in params]
        values = [self.to_float(self.process_unused(ss)) for ss in values]

        for ii, par in enumerate(params):
            val = values[ii]
            self.__setattr__(par, val)

        if len(values) > len(params):
            self.additional_parameters = values[len(params):]

        if "parameters" in params:
            self.process_parameters()

    def process_unused(self, val):

        if (type(val) is str) and (val.lower() in ["na", "unused"]):
            return None
        return val

    def to_float(self, val):

        try: 
            val = float(val)
        except (ValueError, TypeError):
            pass
        return val

    def process_parameters(self):

        if self.parameters is None:
            self.parameters = dict()
            return

        parameters = re.findall("(\w+)\s*=\s*(\w+)", self.parameters)
        self.parameters = dict([(kk, self.process_unused(vv)) for (kk, vv) in parameters])

    def to_epoch(self, start_time, end_time):

        epoch = Epoch(label="Stim%d" % self.number, 
            time=start_time,
            duration=(end_time - start_time), 
            **self.__dict__)

        return epoch


def read_stim_protocol_file(protocol_file, columns=['number',
                                                    'original_wavfile', 
                                                    'tdt_wavefile', 
                                                    'stim_class', 
                                                    'type', 
                                                    'source', 
                                                    'source_sex', 
                                                    'parameters']):
    '''
    Each row in protocol file goes:
    1. Stimulus number
    2. Original wavefile name
    3. TDT's wavefile name
    4. Stimulus class (e.g. Con)
    5. Stimulus type (e.g. Call)
    6. Stimulus source (e.g. Unfamiliar)
    7. Stimulus source sex (e.g. f)
    8. Stimulus parameters

    This can be changed by supplying a different value for columns
    '''

    with open(protocol_file, 'r') as f:
        creader = csv.reader(f, delimiter='\t')
        stimuli = dict()
        for row in creader:
            stimuli[float(row[0])] = Stimulus(columns, row)

    return stimuli

def parse_segment_name(seg):

    print "Processing segment named %s" % seg.name
    # Get site and protocol information from segment name
    try:
        site_name = re.match(r"^(Site\d+)", seg.name).groups()[0]
        print "Site: %s" % site_name
    except IndexError:
        print "Segment name %s appears to be malformed: no site name" % seg.name
        site_name = None

    try:
        protocol_name = re.match(r".*_([A-Za-z0-9]+)$", seg.name).groups()[0]
        print "Protocol: %s" % protocol_name
    except IndexError:
        print "Segment name %s appears to be malformed: no protocol name" % seg.name
        protocol_name = None

    try:
        depths = re.findall("([LR]\d+)", seg.name)
    except IndexError:
        print "Segment name %s appears to be malformed: no depth information" % seg.name
        depths = []

    return site_name, protocol_name, depths


def import_tdt_to_neo(path, stimulus_file, output_file=None, num_arrays=None, num_electrodes_per_array=16):

    # Notes: Neo version 0.4 will replace epoch, analogsignal, event, and spiketrain with arrays
    # This is the hdf5 sound manager from neosound
    sm = SoundManager(HDF5Store, stimulus_file)
    print "Reading TDT files from %s" % path
    r = TdtIO(path)
    # Read the block from the specified tdt tank
    output_blk = r.read()[0]

    print "Found %d recording segments" % len(output_blk.segments)

    site_names = dict()
    blks = list()

    # Each segment in output_blk is a protocol. Need to create blocks that correspond to sites and segments that correspond to protocols within each site
    for seg in output_blk.segments:
        print "Processing segment named %s" % seg.name
        # Get site and protocol information from segment name
        try:
            site_name = re.match(r"^(Site\d+)", seg.name).groups()[0]
            print "Site: %s" % site_name
        except IndexError:
            print "Segment name %s appears to be malformed: no site name" % seg.name
            site_name = None

        try:
            protocol_name = re.match(r".*_([A-Za-z0-9]+)$", seg.name).groups()[0]
            print "Protocol: %s" % protocol_name
        except IndexError:
            print "Segment name %s appears to be malformed: no protocol name" % seg.name
            protocol_name = None

        try:
            depths = re.findall("([LR]\d+)", seg.name)
        except IndexError:
            print "Segment name %s appears to be malformed: no depth information" % seg.name
            depths = []

        # Create a new block if this is a new site
        if site_name not in site_names:
            print "Creating site named %s " % site_name,
            blk = Block(name=site_name)
            blks.append(blk)
            site_names[site_name] = blk
            # Annotate the block with depth items
            depthstr = []
            for depth in depths:
                key, value = re.match("([^0-9]+)([0-9]+)", depth).groups()
                key = "%sdepth" % key.lower()
                value = int(value) / 2 * pq.um
                blk.annotations[key] = value
                depthstr.append("with depth labeled %s of %d" % (key, value))
            print " and ".join(depthstr)

            # Create the electrode array(s)
            if num_arrays is None:
                channel_indices = np.unique([ansig.channel_index for ansig in seg.analogsignals])
                num_arrays = len(channel_indices) / num_electrodes_per_array
                print "Found %d recording channels" % len(channel_indices)

            print "Creating %d arrays with %d recording channels each" % (num_arrays, num_electrodes_per_array)
            for ii in range(num_arrays):
                inds = channel_indices[ii * num_electrodes_per_array: (ii + 1) * num_electrodes_per_array]
                rcg = RecordingChannelGroup(name="Array %d" % ii, channel_indexes=inds)
                blk.recordingchannelgroups.append(rcg)

        else:
            blk = site_names[site_name]

        # Modify the segment
        new_seg = Segment(name=protocol_name)


        # Add all of the lfps to their corresponding electrode
        print "Collecting all LFP objects"
        for ansig in seg.analogsignals:
            if not ansig.name.upper().startswith("LFP"):
                continue

            # Get the corresponding electrode array - it should definitely exist
            array_ind = int((ansig.channel_index - 1) / num_electrodes_per_array)
            rcg = blk.filter(container=True, objects=RecordingChannelGroup, name="Array %d" % array_ind)[0]
            
            # Get the corresponding electrode or create one if it doesn't exist
            rc = rcg.filter(objects=RecordingChannel, index=ansig.channel_index)
            if len(rc):
                rc = rc[0]
            else:
                print "Creating recording channel %d" % ansig.channel_index
                rc = RecordingChannel(index=ansig.channel_index)
                rc.recordingchannelgroups.append(rcg)
                rcg.recordingchannels.append(rc)

            # Store the lfp
            print "Storing lfp data in recording channel %d" % rc.index
            rc.analogsignals.append(ansig)
            new_seg.analogsignals.append(ansig)

        # Add all of the units to their corresponding electode array with identifiers for which electrode they came from
        # Unfortunately the units are a child of recordingchannelgroups; perhaps we should subclass recordingchannels and 
        # recordingchannelgroups to form something more appropriate for our electrodes and electrode arrays
        print "Collecting all spiketrains"
        for st in seg.spiketrains:
            # Get the corresponding electrode array - it should definitely exist
            ci = st.annotations["channel_index"]
            sort_code = int(re.findall("Code(\d+)", st.name)[0])
            array_ind = int((ci - 1) / num_electrodes_per_array)
            rcg = blk.filter(container=True, objects=RecordingChannelGroup, name="Array %d" % array_ind)[0]

            # Get the corresponding unit or create one if it doesn't exist
            unit = rcg.filter(objects=Unit, name=st.name)
            if len(unit):
                if len(unit) > 1:
                    print "Found multiple units with the same channel index and sort code!"
                unit = unit[0]
            else:
                print "Creating unit with channel index %d and sort code %d" % (ci, sort_code)
                unit = Unit(channel_indexes=[ci],
                            name=st.name,
                            region=None,
                            subregion=None,
                            sort_type=sort_code,
                            extra_info=None)
                unit.recordingchannelgroup = rcg
                rcg.units.append(unit)

            # Store the spiketrain
            print "Storing spiketrain data in unit %s" % unit.name
            unit.spiketrains.append(st)
            new_seg.spiketrains.append(st)

        # Get the stimuli
        print "Collecting information on the stimuli"
        stim_on = seg.filter(objects=EventArray, name="Stm+")[0]
        stim_off = seg.filter(objects=EventArray, name="Stm-")[0]
        assert len(stim_on.times) == len(stim_off.times)
        print "Played %d stimuli in this recording segment" % len(stim_on.times)

        for stim_num, start, stop in zip(stim_on.labels, stim_on.times, stim_off.times):
            stim_id = sm.database.filter_ids(number=float(stim_num))[0]
            epoch = Epoch(label="Stim%d" % int(float(stim_num)),
                          time=start,
                          duration=(stop - start),
                          stim_id=stim_id,
                          number=float(stim_num),
                          )
            print "Creating epoch with label %s, starting at %4.1f, associated with stimulus %d" % (epoch.label,
                                                                                                    epoch.time,
                                                                                                    epoch.annotations["stim_id"])
            new_seg.epochs.append(epoch)

        blk.segments.append(new_seg)

        # Reset all of the relationships to the new structure
        blk.create_many_to_one_relationship(force=True, recursive=True)

    if output_file is not None:
        of = NeoHdf5IO(output_file)
        of.write_all_blocks(blks)
        of.close()

    return blks


if __name__ == "__main__":

    from neurotables.neo.tdt import *
    path = "/auto/k8/fdata/tlee/tdt_raw/LbBla4218M"
    sound_file = "/auto/k8/fdata/tlee/test_paired_stim.h5"
    ephys_file = "/auto/k8/fdata/tlee/test_tdt_output_TL.h5"
    blks = import_tdt_to_neo(path, sound_file, ephys_file)
    r = TdtIO(path)
    output_blk = r.read()[0]
