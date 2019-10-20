from . import utilities
import os
import h5py
import numpy as np

class Dataset:
    _subsets = []
    def __init__(self, filename=None):
        """
        Creates the hdf5 file for saving.
        """
        self.filename = filename

    def get(self, path,slice = False):
        """
        Gets the element of the hdf5 at path. Path must be a string of
        keys seperated by '/'. If path does not descend to a dataset in the h5,
        then it will return a dictionary with nested keys in the structure of
        the subgroup of the h5. If path does reach a dataset, and that dataset
        is an array, you may give a slice object to specify what data you want
        from the array
        """
        datadict = {}
        def _loaddict(path, obj):
            """
            Takes the path to an object in an h5 file and the object itself.
            If the object is a group, does nothing, but if the object is a
            dataset, finds the equivalent place in datadict (creating nested
            dics if needed), and puts the contents of obj there.
            """
            if isinstance(obj, h5py._hl.dataset.Dataset):
                listpath = path.split('/')#split the path into individual keys
                currentdictlevel = datadict
                for key in listpath[:-1]: #iterate through all keys except the last
                    if not key in currentdictlevel.keys():
                        currentdictlevel[key] = {} #if it doesn't exist, create it
                    currentdictlevel = currentdictlevel[key] #go down one level
                currentdictlevel[listpath[-1]] = obj[...]
                #at the bottom, set the key value equal to the contents of the obj.
        f = h5py.File(self.filename,'r') #opens the h5 file
        loc = False
        if isinstance(f[path],h5py._hl.dataset.Dataset):
            #is the thing you asked for a dataset, or a group?
            if slice:
                toreturn = f[path][slice]
            else:
                toreturn = f[path][...]
        elif isinstance(f[path],h5py._hl.group.Group):
            datadict = {}
            f.visititems(_loaddict)
            #visititems recursively applies loaddict at every item of path.
            #datadict modified by reference.
            toreturn = datadict
        else:
            raise Exception('Unrecognized h5 type at specified path')
            toreturn = None
        f.close()
        return toreturn

    def append(self, pathtowrite, datatowrite, slice = False):
        """
        Adds new data to dataset at path. Data may be a string, number, numpy
        array, or a nested dict. If a nested dict, leaves must be strings,
        numbers or numpy arrays. Data may not overwrite, however, dicts can be
        used that go through HDF5 groups that already exist.
        """
        cleandatatowrite = self.sanitize(datatowrite)
        if isinstance(cleandatatowrite, dict):
            def _loadhdf5(path, obj):
                """
                Takes the path to an object in an dict file and the object
                itself. If the object is a dict, does nothing, but if the
                object is not, finds the equivalent place in f (creating nested
                groups if needed), and puts the contents of obj there.
                """
                sep = '/'
                h5path = pathtowrite + sep.join(path)
                if not isinstance(obj, dict):
                    self._writetoh5(data = obj, path = h5path)
            self.dictvisititems(cleandatatowrite, _loadhdf5)
        elif isinstance(cleandatatowrite, np.ndarray) and slice:
                    self._appenddatah5(self.filename, cleandatatowrite,
                                                             pathtowrite,slice)
        else:
            self._writetoh5(data = cleandatatowrite, path = pathtowrite)



    def _writetoh5(self, **kwargs):
        """
        Tries to write to h5, giving an opportunity to change path
        if there is already data at the path. This only writes complete
        objects to fresh datasets.
        Keyword arguments:

        data (numpy array, str or number): the data to be written. Numpy
                                            arrays must already be sanitized
                                            to ensure they do not contain
                                            objects.

        path (str): location to write data. should be in hdf5 path format.
        """
        f = h5py.File(self.filename,'a')
        try:
            f[kwargs['path']]
            f.close()
            newpath = input('Path ' + kwargs['path'] +
                            ' has been used already! Type a new path: ')
            kwargs['path']=newpath
            self._writetoh5(**kwargs)
        except KeyError:
            f.create_dataset(kwargs['path'], data = kwargs['data'])
            f.close()


    def dictvisititems(self, dictionary, function):
        """
        Applies function at every node of nested dict, passing the path as a
        list as the first argument, and the object itself as the second.
        """
        def recursivevisit(dictionary, function, keylist):
            for key in dictionary.keys():
                function(keylist + [key], dictionary[key])
                if isinstance(dictionary[key], dict):
                    recursivevisit(dictionary[key], function, keylist + [key])
        recursivevisit(dictionary, function, [])

    def _appenddatah5(self, filename, numpyarray, pathtowrite, slice):
        """
        Adds data to an existing array in a h5 file. Can only overwrite nan's,
        such arrays should be instantiated with writetoh5
        """
        f = h5py.File(filename,'r+')
        dataset = f[pathtowrite]
        if np.shape(numpyarray) !=  np.shape(dataset[slice]):
            f.close()
            raise Exception('Slice and data are not the same shape')
        if np.all(np.isnan(dataset[slice])):
            dataset[slice] = numpyarray
            f.close()
        else:
            shouldoverwrite = input('Data already written to ' + pathtowrite +
                                    ' at location ' + str(slice) +
                                    '. Type OVERWRITE to overwrite, else, code'
                  ' creates a new array at path+_antioverwrite and saves data '
                                                                   + 'there')
            if shouldoverwrite == 'OVERWRITE':
                dataset[slice] = numpyarray
                f.close()
            else:
                fao = h5py.File('antioverwrite_' + filename,'a')
                try:
                    fao.create_dataset(pathtowrite, shape = np.shape(dataset))
                    f[pathtowrite][slice] = numpyarray
                    fao.close()
                    f.close()
                    print('this')
                except:
                    fao.close()
                    f.close()
                    self._appenddatah5(filename + '_antioverwrite', numpyarray,
                                            pathtowrite, slice)

    def sanitize(self,data):
        """
        Sanitizes input before loading into an h5 file. If sanitization fails,
        prints a message and converts to a string.
        """
        allowedtypes = ['float', 'int','complex', 'uint']
        allowednonnumpytypes = [str, float, int, list]
        if type(data) in allowedtypes + allowednonnumpytypes:
            cleandata = data
        elif type(data) == np.ndarray:
            if data.dtype in [np.dtype(a) for a in allowedtypes]:
                cleandata = data
            else:
                try:
                    cleandata = np.array(data, dtype = 'float')
                except ValueError:
                    print('Could not convert dtype of numpy array to float.'
                          +' Saving as a string')
                    cleandata = str(data)
        elif isinstance(data, dict):
            cleandata = {}
            for key in data.keys():
                cleandata[key] = self.sanitize(data[key])
        else: #todo: add conversion to utf-8 for string containing numpys
            print('Could not recognize type. Attempting to convert to string.')
            try:
                cleandata = str(data)
            except:
                shouldcontinue = input('COULD NOT CONVERT TO STRING. '
                + 'DATA WILL NOT BE SAVED. Continue y/(n)')
                if shouldcontinue != 'y':
                    raise Exception('TypeError: could not convert to h5')
                cleandata = 'unconvertable'
        return cleandata

    def get_computer_name():
        computer_name = utilities.get_computer_name()
        aliases = {'SPRUCE': 'bluefors', 'HEMLOCK': 'montana'} # different names we want to give the directories for each computer
        if computer_name in aliases.keys():
            computer_name = aliases[computer_name]
        return computer_name

    def get_data_server_path():
        """
        Returns full path of the data server's main directory, formatted based on OS.
        """
        if platform.system() == 'Windows':
            return r'\\SAMBASHARE\labshare\data'
        elif platform.system() == 'Darwin': # Mac
            return '/Volumes/labshare/data/'
        elif platform.system() == 'Linux':
            return '/mnt/labshare/data/'
        else:
            raise Exception('What OS are you using?!? O_O')


    def get_local_data_path():
        """
        Returns full path of the local data directory.
        """
        return os.path.join(
                    os.path.expanduser('~'),
                    'data',
                    get_computer_name(),
                    'experiments'
                )


    def get_remote_data_path():
        """
        Returns full path of the remote data directory.
        """
        return os.path.join(
                    get_data_server_path(),
                    get_computer_name(),
                    'experiments'
                )
