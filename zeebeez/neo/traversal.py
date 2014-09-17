from neo import NeoHdf5IO

def get_site(neo_file, site_number):

    neo_manager = NeoHdf5IO(neo_file)
    blks = neo_manager.read_all_blocks(cascade=False, lazy=True)
    site_str = "Site%d" % site_number
    blk_loc = [blk.hdf5_path for blk in blks if blk.name == site_str]
    if len(blk_loc):
        blk = neo_manager.get(path=blk_loc[0], lazy_loaded=True)
        blk.create_many_to_one_relationship()
    else:
        blk = None

    neo_manager.close()
    return blk





