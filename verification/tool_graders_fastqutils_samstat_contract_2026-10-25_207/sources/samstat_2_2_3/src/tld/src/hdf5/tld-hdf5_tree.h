#ifndef TLD_HDF5_TREE_H
#define TLD_HDF5_TREE_H

#ifdef TLD_HDF5_TREE_IMPORT
#define EXTERN
#else
#define EXTERN extern
#endif

struct hdf5_data;
struct hdf5_node;

EXTERN int hdf5_data_exists(struct hdf5_data *d, char *name, char **path);
EXTERN int hdf5_build_tree(struct hdf5_data *d);
EXTERN void hdf5_node_free(struct hdf5_node *n);
#undef TLD_HDF5_TREE_IMPORT
#undef EXTERN


#endif
