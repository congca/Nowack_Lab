import xarray as xr
import numpy as np
from importlib import reload
import h5py
import json

class Xarray:
    '''
    Features:
    - returns Nowack_Lab.Procedures as xarray datasets
    - datasets are organized logically with units and labels
    - datasets can be saved and loaded with h5netcdf

    Warnings:
    - netcdf does not support booleans.  It will import correctly, but not 
      save correctly.  To avoid, but not solve, the problem, save with 
      'h5netcdf' engine.  h5netcdf casts the boolean into an int and 
      handles it on load.  
    '''
    
    @staticmethod
    def scanplane(fullpath):
        '''
        Warnings:
        ~~~~~~~~~
          - this might not work for fast_y.  The x,y might be flipped
        '''
        # load the scanplane
        import Nowack_Lab.Procedures.scanplane
        reload(Nowack_Lab.Procedures.scanplane)
        from Nowack_Lab.Procedures.scanplane import Scanplane
        sp = Scanplane.load(fullpath)

        sp_x = sp.X[0,:]
        sp_y = sp.Y[:,0]

        dc = xr.DataArray(sp.V['dc'], dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='dc SQUID data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })
        acx = xr.DataArray(sp.V['acx'], dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='AC x SQUID data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })
        acy = xr.DataArray(sp.V['acy'], dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='AC y SQUID data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })
        cap = xr.DataArray(sp.V['cap'], dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='Capacitance data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })
        z   = xr.DataArray(sp.Z, dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='Z height data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })

        squidarray = Xarray.notNone(sp.squidarray, 
                                    sp.plane.instruments['squidarray'], None)
        preamp = Xarray.notNone(sp.preamp, sp.plane.instruments['preamp'], None)
        lockin_current = Xarray.notNone(sp.lockin_current, 
                                        sp.plane.instruments['lockin_current'], None)
        lockin_squid = Xarray.notNone(sp.lockin_squid, 
                                        sp.plane.instruments['lockin_squid'], None)
        lockin_cap = Xarray.notNone(sp.lockin_cap, 
                                        sp.plane.instruments['lockin_cap'], None)
        
        
        #make dataset 
        ds = xr.Dataset({'dc': dc, 'acx':acx, 'acy': acy, 'cap': cap, 'z': z,
                        'squidarray':Xarray.toblankdataarray(squidarray),
                        'preamp':Xarray.toblankdataarray(preamp),
                        'lockin_current':Xarray.toblankdataarray(lockin_current),
                        'lockin_squid':Xarray.toblankdataarray(lockin_squid),
                        'lockin_cap':Xarray.toblankdataarray(lockin_cap),
                        },
                        attrs={'filename': sp.filename,
                              'scan_rate': sp.scan_rate,
                              'scan_height': sp.scanheight,
                              'time_elapsed_s': sp.time_elapsed_s,
                              'timestamp': sp.timestamp,
                              'interrupt': sp.interrupt,
                              'fast_axis': sp.fast_axis,
                              'center': sp.center,
                            'loadpath': fullpath,
                              }
                        )
        return ds

    @staticmethod
    def scanspectra(fullpath, transposed=False, reshape=False):
        '''
        '''

        # load the scanspectra
        import Nowack_Lab.Procedures.scanspectra
        reload(Nowack_Lab.Procedures.scanspectra)
        from Nowack_Lab.Procedures.scanspectra import Scanspectra
        sp = Scanspectra.load(fullpath)

        sp_x = sp.X[0,:]
        sp_y = sp.Y[:,0]

        dims = ['y', 'x', 't'] if transposed else ['x', 'y', 't']

        if reshape:
            print('reshaping')
            sp_V = sp.V.reshape(sp_x.shape[0], sp_y.shape[0], sp.t.shape[0])
            sp_psdAve = sp.psdAve.reshape(sp_x.shape[0], sp_y.shape[0], sp.f.shape[0])
        else:
            sp_V = sp.V
            sp_psdAve = sp.psdAve

        V = xr.DataArray(sp_V, dims=dims, 
                             coords={'x':sp_x, 'y':sp_y, 't':sp.t},
                             name='Voltage Time traces (V)',
                             attrs={'data units': 'Volts',
                                    'x units': 'Volts',
                                    'y units': 'Volts',
                                    't units': 'Seconds',
                                    }
                             )

        dims = ['y', 'x', 'f'] if transposed else ['x', 'y', 'f']

        psdAve = xr.DataArray(sp_psdAve, dims=dims, 
                             coords={'x':sp_x, 'y':sp_y, 'f':sp.f},
                             name='Voltage Time traces (V)',
                             attrs={'data units': 'Volts',
                                    'x units': 'Volts',
                                    'y units': 'Volts',
                                    'f units': 'Hz',
                                    }
                             )

        dims = ['y', 'x'] if transposed else ['x', 'y']
        Z = xr.DataArray(sp.Z, dims=dims, 
                         coords={'x':sp_x, 'y':sp_y},
                         name='Z position (V)',
                         attrs={'data units': 'Volts',
                             'x units': 'Volts',
                             'y units': 'Volts',
                             }
                         )
        try:
            squidarray = Xarray.notNone(sp.squidarray, 
                                        sp.plane.instruments['squidarray'],
                                        sp.instruments['squidarray'])
        except:
            print('Cannot load squidarray')
            squidarray={}
        try:
            preamp = Xarray.notNone(sp.preamp, sp.plane.instruments['preamp'],
                                    sp.instruments['preamp'])
        except:
            print('Cannot load preamp')
            preamp={}

        #lockin_current = Xarray.notNone(sp.lockin_current, 
        #                                sp.plane.instruments['lockin_current'],
        #                                sp.instruments['lockin_current'])
        #lockin_squid = Xarray.notNone(sp.lockin_squid, 
        #                                sp.plane.instruments['lockin_squid'],
        #                                sp.instruments['lockin_squid'])
        #lockin_cap = Xarray.notNone(sp.lockin_cap, 
        #                                sp.plane.instruments['lockin_cap'],
        #                                sp.instruments['lockin_cap'])

        # make dataset
        ds = xr.Dataset({'V': V, 'psdAve':psdAve, 'z': Z, 
                        'preamp':Xarray.toblankdataarray(preamp, 'preamp'),
                        'squidarray':Xarray.toblankdataarray(squidarray, 'preamp'),
                        },
                        attrs={'filename': sp.filename,
                               'monitor_time': sp.monitor_time,
                               'num_averages': sp.num_averages,
                               'numpts': sp.numpts,
                               'sample_rate': sp.sample_rate,
                               'scanheight': sp.scanheight,
                               'timestamp': sp.timestamp,
                               'time_elapsed_s': sp.time_elapsed_s,
        #                      'lockin_current': lockin_current,
        #                      'lockin_squid': lockin_squid,
        #                      'lockin_cap': lockin_cap
                            'loadpath': fullpath,
                              }
                        )
        return ds

    @staticmethod
    def arraytunebatch1(fullpath):
        '''
        this will probably change considerably if/when we rework 
        arraytunebatch
        '''
        import Nowack_Lab.Procedures.array_tune
        reload(Nowack_Lab.Procedures.array_tune)
        from Nowack_Lab.Procedures.array_tune import ArrayTuneBatch
        atb = ArrayTuneBatch.load(fullpath)

        sflux = atb.sflux
        sbias = atb.sbias
        aflux = atb.aflux

        dims = ['sbias', 'aflux', 'sflux']

        char_saasig = xr.DataArray(atb.char_saasig, 
                                       dims= dims + ['t'],
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 },
                                       name='SAA signal for characteristic (Volts)',
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )

        char_testsig = xr.DataArray(atb.char_testsig, 
                                       dims= dims + ['t'],
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 },
                                       name='Test signal for characteristic (Volts)',
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        spectrum_mean = xr.DataArray(atb.spectrum_mean[...,0], 
                                       dims= dims,
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 },
                          name='Mean w.r.t frequency of Noise Spectrum (phi_0)',
                                       attrs={'data units': 'phi_0',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        spectrum_std = xr.DataArray(atb.spectrum_std[...,0], 
                                       dims= dims,
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 },
            name='Standard deviation w.r.t frequency of Noise Spectrum (phi_0)',
                                       attrs={'data units': 'phi_0',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        spectrum_psd = xr.DataArray(atb.spectrum_psd, 
                                       dims= dims + ['frequency'],
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 'frequency': atb.spectrum_f,
                                                 },
                          name='Mean w.r.t frequency of Noise Spectrum (phi_0)',
                                       attrs={'data units': 'phi_0',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              'frequency':   'Hz',
                                              },
                                       )
        filenames = np.full(atb.filenameindex.shape, 
                            max(atb.arraytunefilenames, key=len)
                           )
        shape = filenames.shape
        for i in range(filenames.flatten().shape[0]):
            index = np.unravel_index(i, shape)
            if np.isnan(atb.filenameindex[index]):
                filenames[index] = 'N/A: Did Not Lock'
                continue
            filenames[index] = atb.arraytunefilenames[int(atb.filenameindex[index])]

        atfilenames = xr.DataArray(filenames[...,0],
                                        dims = dims,
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                },
                                       name='Array Tune filenames (string)',
                                       attrs={'data units': 'string',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        char_lockpt_mean = xr.DataArray(atb.char_stats[...,0], 
                                     dims=dims,
                                     coords = {'sbias': sbias,
                                               'aflux': aflux,
                                               'sflux': sflux,
                                              },
                                     name=('Squid Characteristic statistics: ' + 
                                           'average of the value near the lockpoint ' +
                                           '(Volts)'),
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        char_lockpt_grad = xr.DataArray(atb.char_stats[...,1], 
                                     dims=dims,
                                     coords = {'sbias': sbias,
                                               'aflux': aflux,
                                               'sflux': sflux,
                                              },
                           name=('Squid Characteristic statistics: ' + 
                                 'average of the gradient near the lockpoint ' +
                                 '(Volts)'),
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        char_lockpt_err = xr.DataArray(atb.char_stats[...,2], 
                                     dims=dims,
                                     coords = {'sbias': sbias,
                                               'aflux': aflux,
                                               'sflux': sflux,
                                              },
                                     name=('Squid Characteristic statistics: ' + 
                                           'average of the error in the fit near ' + 
                                           'the lockpoint (Volts)'),
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        char_lockpt_good = xr.DataArray(atb.char_stats[...,3], 
                                     dims=dims,
                                     coords = {'sbias': sbias,
                                               'aflux': aflux,
                                               'sflux': sflux,
                                              },
                                     name=('Squid Characteristic statistics: ' + 
                                           'average of the gradient/error near ' + 
                                           'the lockpoint (Volts)'),
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        # make dataset
        ds = xr.Dataset({'char_saasig': char_saasig, 
                         'char_testsig': char_testsig,
                         'spectrum_mean': spectrum_mean,
                         'spectrum_std': spectrum_std,
                         'spectrum_psd': spectrum_psd,
                         'arraytune_filenames': atfilenames,
                         'char_lockpt_mean': char_lockpt_mean,
                         'char_lockpt_grad': char_lockpt_grad,
                         'char_lockpt_err': char_lockpt_err,
                         'char_lockpt_good': char_lockpt_good,
                        },
                        attrs={'filename': atb.filename,
                               'timestamp': atb.timestamp,
                               'time_elapsed_s': atb.time_elapsed_s,
                               'conversion': atb.conversion,
                            'loadpath': fullpath,
                              }
                        )
        return ds
        
    @staticmethod
    def bestlockpoint(fullpath):
        import Nowack_Lab.Procedures.array_tune
        reload(Nowack_Lab.Procedures.array_tune)
        from Nowack_Lab.Procedures.array_tune import BestLockPoint
        blp = BestLockPoint.load(fullpath)

        dims = ['sbias']
        sbias = blp.sbiasList
        time = blp.bestloc_raw_time[0] # all times are the same
        
        char_timesort = xr.DataArray(np.dstack([blp.bestloc_raw_test, 
                                                blp.bestloc_raw_saa]), 
                                  dims=dims + ['time', 'params_timesort'],
                                  coords={'sbias': sbias,
                                          'time' : time,
                                          'params_timesort': ['test', 'saa']},
                                  name='{Test, SAA} Signal sorted by time (V)',
                                  attrs={'data units': 'Volts',
                                         'sbias units': 'Micro Amps',
                                         'time units' : 'Seconds'
                                        },
                                  )
        sbiasfull = np.tile(sbias, (blp.bestloc_testsort_saa.shape[1],1)).T

        char_testsort = xr.DataArray(np.dstack([blp.bestloc_testsort_saa,
                                                blp.bestloc_mean,
                                                blp.bestloc_grad,
                                                blp.bestloc_err,
                                                blp.bestloc_absgrad_over_err]),
                                  dims=dims + ['test_i', 'params_testsort'],
                                  coords={'sbias': sbias,
                                          'params_testsort': ['saa', 'smoothed',
                                                     'gradient', 'error', 
                                                     'gradient_error'],
                                          'test_V': (('sbias', 'test_i'), 
                                                    blp.bestloc_testsort_test),
                                          'sbias_full': (('sbias', 'test_i'), 
                                                         sbiasfull),
                                          },
                                  name='Signals sorted by test signal (V)',
                                  attrs={'data units': 'Volts',
                                         'sbias units': 'Micro Amps',
                                         'test meaning': 'Test Signal in Volts',
                                         'saa meaning': 'SAA Signal in Volts',
                                         'smoothed meaning': 
                                            'Smoothed SAA Signal in Volts',
                                         'gradient meaning': 
                                            'Gradient of smoothed SAA Signal in Volts',
                                         'error meaning': 
                                            '(smoothed - saa) signal in Volts',
                                         'gradient_error meaning':
                                            'gradient / error signal in Volts'
                                        },
                                  )
        ds = xr.Dataset({'char_timesort':char_timesort,
                         'char_testsort':char_testsort,
                         'preamp':Xarray.toblankdataarray(blp.preamp, 
                                                          'preamp'),
                         'squidarray':Xarray.toblankdataarray(blp.squidarray, 
                                                              'squidarray'),
                         },
                         attrs={'filename':  blp.filename,
                                'timestamp': blp.timestamp,
                                'monitortime': blp.monitortime,
                                'samplerate': blp.samplerate,
                                'testinputconv': blp.testinputconv,
                                'loadpath': fullpath,
                                }
                         )
        return ds

    @staticmethod
    def gmf_monitorattrs_1(fullpath):
        [my_h5, my_json] = Xarray.dumbloader1(fullpath)

        data = xr.DataArray(np.vstack([my_json['data']['X'],
                                        my_json['data']['Y'],
                                        my_json['data']['X_harm3'],
                                        my_json['data']['Y_harm3'],
                                        ]).T,
                            dims=['T', 'data_params'],
                            coords={'T': my_json['data']['T'],
                                    'data_params': ['X', 'Y', 
                                                    'X_harm3', 'Y_harm3'],
                                   },
                            name='Data (V)',
                            attrs={'X units': 'Volts',
                                   'Y units': 'Volts',
                                   'X_harm3 units': 'Volts',
                                   'Y_harm3 units': 'Volts',
                                   'T units': 'Kelvin',
                                   }
                            )
        ds = xr.Dataset( {'data': data,
                          'preamp': Xarray.toblankdataarray(
                                my_json['preamp']['py/state'], 'preamp'),
                          'squidarray': Xarray.toblankdataarray(
                                my_json['squidarray']['py/state'], 'squidarray'),
                          },
                          attrs={'filename': my_json['filename'],
                                 'loadpath': fullpath,
                                 'timestamp': my_json['timestamp'],
                                 'time_elapsed_s': my_json['time_elapsed_s'],
                                 'loadpath': fullpath,
                                 }
                          )
        return ds

    @staticmethod
    def heightsweep(fullpath):
        import Nowack_Lab.Procedures.heightsweep
        reload(Nowack_Lab.Procedures.heightsweep)
        from Nowack_Lab.Procedures.heightsweep import Heightsweep
        hs = Heightsweep.load(fullpath)

        v = xr.DataArray(np.vstack([
                                    hs.Vup['acx'],
                                    hs.Vup['acy'],
                                    hs.Vup['cap'],
                                    hs.Vup['dc'],
                                    hs.Vdown['acx'][::-1],
                                    hs.Vdown['acy'][::-1],
                                    hs.Vdown['cap'][::-1],
                                    hs.Vdown['dc'][::-1],
                                    ]).T,
                        dims=['z', 'v_params'],
                        coords={'z': hs.Vup['z'],
                                'v_params': ['acx_up', 'acy_up',
                                             'cap_up', 'dc_up',
                                             'acx_down', 'acy_down',
                                             'cap_down', 'dc_down',
                                             ]
                                },
                        attrs={
                               'acx_up units': 'Volts',
                               'acy_up units': 'Volts',
                               'cap_up units': 'Volts',
                               'dc_up units' : 'Volts',
                               'acx_down units': 'Volts',
                               'acy_down units': 'Volts',
                               'cap_down units': 'Volts',
                               'dc_down units' : 'Volts',
                               'z units': 'Volts'
                               }
                        )
        ds = xr.Dataset( {'v': v,
                          'preamp': Xarray.toblankdataarray(
                              hs.plane.instruments['preamp'], 'preamp'),
                          'squidarray': Xarray.toblankdataarray(
                              hs.plane.instruments['squidarray'],
                              'squidarray'),
                          'lockin_squid': Xarray.toblankdataarray(
                              hs.lockin_squid, 'lockin_squid'),
                          },
                          attrs={
                            'scan_rate': hs.scan_rate,
                            'time_elapsed_s': hs.time_elapsed_s,
                            'timestamp': hs.timestamp,
                            'x': hs.x,
                            'y': hs.y,
                            'z0': hs.z0,
                            'filename': hs.filename,
                            'loadpath': fullpath,
                            }
                          )
        return ds




        
    @staticmethod
    def notNone(a, b, c):
        if a is None and b is None:
            return c
        elif a is None:
            return b
        return a

    @staticmethod
    def toblankdataarray(dictionary, name):
        return xr.DataArray([], dims=None, coords=None, name=name, 
                            attrs=dictionary)

    @staticmethod
    def dumbloader1(path):
        file_h5 = h5py.File(path + '.h5', 'r') # access with file_h5['keyname'].value
        with open(path + '.json', 'r') as f:
            file_json = json.load(f)['py/state']

        return [file_h5, file_json]

    @staticmethod
    def save(ds, filename):
        ds.to_netcdf(filename, format='NETCDF4', engine='h5netcdf')

    @staticmethod
    def load(filename):
        return xr.open_dataset(filename, engine='h5netcdf')

    @staticmethod
    def save_compressed(ds, filename):
        comp = dict(zlib=True, complevel=9)
        encoding = {var: comp for var in ds.data_vars}
        ds.to_netcdf(filename, format='NETCDF4', engine='h5netcdf',
                    encoding=encoding)

