"""
Nowack_Lab high level driver for Zurich HF2LI

Needs: zhinst, numpy, .instrument, time and _future_
"""

# Copyright 2016 Zurich Instruments AG

from __future__ import print_function
import time
from .instrument import Instrument
import numpy as np
import zhinst.utils

class gateVoltageError( Exception ):
    pass


class HF2LI(Instrument):
    '''
    Creates a Zurich HF2Li object, to control a zurich lock in amplifier
    '''

    _label = 'Zurich HF2LI'

    def __init__(self, server_address = 'localhost', server_port = 8005 ,
                device_serial = ''):
        '''
        Creates the HF2LI object. By choosing server address, can connection
        to HF2LI on remote (local network) computer.

        Arguments:

        server_address (str,optional) = Private IPV4 address of the computer
                            hosting the zurich. Defults to 'localhost',
                            the computer the python kernel is running on.

        server_port (int, optional) = Port of Zurich HF2LI. For local is
                            always 8005 (default), usually 8006 for remote.

        device_serial (str, optional) = Serial number of prefered zurich
                            hf2li. If empty string or does not exist,
                            uses first avaliable ZI.

        '''
        # Accesses the DAQServer at the instructed address and port.
        self.daq = zhinst.ziPython.ziDAQServer(server_address, server_port)
        # Gets the list of ZI devices connected to the Zurich DAQServer
        deviceList = zhinst.utils.devices(self.daq)

        # Checks if the device serial number you asked for is in the list
        if device_serial in deviceList :
            # Sets class variable device_id to the serial number
            self.device_id = device_serial
            # Tells the user that the ZI they asked for was found
            print('Using Zurich HF2LI with serial %s' % self.device_id)

        # Checks if you actually asked for a specific serial
        elif device_serial != '' :
            # Tells user ZI wasn't found.
            print('Requested device not found.')
            # Sets device_id to the first avaliable. Prints SN.
            self.device_id = zhinst.utils.autoDetect(self.daq)
        else:
            # Sets device_id to the first avaliable. Prints SN.
            self.device_id = zhinst.utils.autoDetect(self.daq)


    def freq_sweep(self, freq_start, freq_stop, num_steps, time_constant = 1e-3,
                 amplitude = .1, outputchan = 1, inputchan = 1, couple = 'ac',
                 settleTCs = 10, avgTCs = 5, loopcount = 1, do_plot=True):
        """
        Sweeps frequency of chosen oscillator, while recording chosen input.

        Citation: Adapted from Zurich Instruments' "sweep" example.

        Arguments:

          freq_start (float): start frequency of sweep in hz

          freq_end (float): stop frequency of sweep in hz

          num_steps (int): number of frequency steps to perform

          time_constant (float): demod timeconstant

          amplitude (float, optional): The amplitude to set on the signal output.

          inputchan (int, optional): input channel (1 or 2)

          outputchan (int, optional): output channel (1 or 2)

          couple (string, optional): ac couple if str = 'ac', o.w. dc couple

          settleTCs (int, optional): number of time constants to allow demod to
            stabilize after sweep.

          avgTCs (int, optional): number of time constants to average demod
            output for data point.

          do_plot (bool, optional): Specify whether to plot the sweep.
           Default is no plot output.

        Returns:

          sample (list of dict): A list of demodulator sample dictionaries. Each
            entry in the list correspond to the result of a single sweep and is a
            dict containing a demodulator sample.

        Raises:

          RuntimeError: If the device is not "discoverable" from the API.

        See the "LabOne Programing Manual" for further help, available:
          - On Windows via the Start-Menu:
            Programs -> Zurich Instruments -> Documentation
          - On Linux in the LabOne .tar.gz archive in the "Documentation"
            sub-folder.

        """

        apilevel_example = 5  # The API level supported by this example.
        # Call a zhinst utility function that returns:
        # - an API session `daq` in order to communicate with devices via the data server.
        # - the device ID string that specifies the device branch in the server's node hierarchy.
        # - the device's discovery properties.
        err_msg = "This example only supports instruments with demodulators."

        # Create a base instrument configuration: disable all outputs, demods and scopes.
        general_setting = [['/%s/demods/*/enable' % self.device_id, 0],
                           ['/%s/demods/*/trigger' % self.device_id, 0],
                           ['/%s/sigouts/*/enables/*' % self.device_id, 0],
                           ['/%s/scopes/*/enable' % self.device_id, 0]]
        self.daq.set(general_setting)
        # Perform a global synchronisation between the device and the data server:
        # Ensure that the settings have taken effect on the device before setting
        # the next configuration.
        self.daq.sync()

        # Now configure the instrument for this experiment. The following channels
        # and indices work on all device configurations. The values below may be
        # changed if the instrument has multiple input/output channels and/or either
        # the Multifrequency or Multidemodulator options installed.
        out_channel = outputchan - 1
        in_channel = inputchan - 1
        demod_index = 0
        osc_index = outputchan-1
        demod_rate = 10e3
        out_mixer_channel = int(self.daq.listNodes('/%s/sigouts/%d/amplitudes/' % (self.device_id, out_channel),0)[0])
        if couple == 'ac':
            acUse = 1
        else:
            acUse = 0
        exp_setting = [['/%s/sigins/%d/ac'             % (self.device_id, in_channel), acUse],
                       ['/%s/sigins/%d/range'          % (self.device_id, in_channel), 2],
                       ['/%s/demods/%d/enable'         % (self.device_id, demod_index), 1],
                       ['/%s/demods/%d/rate'           % (self.device_id, demod_index), demod_rate],
                       ['/%s/demods/%d/adcselect'      % (self.device_id, demod_index), in_channel],
                       ['/%s/demods/%d/order'          % (self.device_id, demod_index), 4],
                       ['/%s/demods/%d/timeconstant'   % (self.device_id, demod_index), time_constant],
                       ['/%s/demods/%d/oscselect'      % (self.device_id, demod_index), osc_index],
                       ['/%s/demods/%d/harmonic'       % (self.device_id, demod_index), 1],
                       ['/%s/sigouts/%d/on'            % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/enables/%d'    % (self.device_id, out_channel, out_mixer_channel), 1],
                       ['/%s/sigouts/%d/range'         % (self.device_id, out_channel),  1],
                       ['/%s/sigouts/%d/amplitudes/%d' % (self.device_id, out_channel, out_mixer_channel), amplitude],
                       ['/%s/sigins/%d/diff'           % (self.device_id, in_channel), 0],
                       ['/%s/sigouts/%d/add'           % (self.device_id, out_channel), 0],
                       ]
        # Some other device-type dependent configuration may be required. For
        # example, disable the signal inputs `diff` and the signal outputs `add` for
        # HF2 instruments.
        self.daq.set(exp_setting)

        # Create an instance of the Sweeper Module (ziDAQSweeper class).
        sweeper = self.daq.sweep()

        # Configure the Sweeper Module's parameters.
        # Set the device that will be used for the sweep - this parameter must be set.
        sweeper.set('sweep/device', self.device_id)
        # Specify the `gridnode`: The instrument node that we will sweep, the device
        # setting corresponding to this node path will be changed by the sweeper.
        sweeper.set('sweep/gridnode', 'oscs/%d/freq' % osc_index)
        # Set the `start` and `stop` values of the gridnode value interval we will use in the sweep.
        sweeper.set('sweep/start', freq_start)
        sweeper.set('sweep/stop', freq_stop)
        # Set the number of points to use for the sweep, the number of gridnode
        # setting values will use in the interval (`start`, `stop`)
        sweeper.set('sweep/samplecount', num_steps)
        # Specify logarithmic spacing for the values in the sweep interval.
        sweeper.set('sweep/xmapping', 1)
        # Automatically control the demodulator bandwidth/time constants used.
        # 0=manual, 1=fixed, 2=auto
        # Note: to use manual and fixed, sweep/bandwidth has to be set to a value > 0.
        sweeper.set('sweep/bandwidthcontrol', 0)
        # Sets the bandwidth overlap mode (default 0). If enabled, the bandwidth of
        # a sweep point may overlap with the frequency of neighboring sweep
        # points. The effective bandwidth is only limited by the maximal bandwidth
        # setting and omega suppression. As a result, the bandwidth is independent
        # of the number of sweep points. For frequency response analysis bandwidth
        # overlap should be enabled to achieve maximal sweep speed (default: 0). 0 =
        # Disable, 1 = Enable.
        sweeper.set('sweep/bandwidthoverlap', 0)

        # Sequential scanning mode (as opposed to binary or bidirectional).
        sweeper.set('sweep/scan', 0)
        # Specify the number of sweeps to perform back-to-back.
        loopcount = 1
        sweeper.set('sweep/loopcount', loopcount)
        # We don't require a fixed sweep/settling/time since there is no DUT
        # involved in this example's setup (only a simple feedback cable), so we set
        # this to zero. We need only wait for the filter response to settle,
        # specified via sweep/settling/inaccuracy.
        sweeper.set('sweep/settling/time', settleTCs*time_constant)
        # The sweep/settling/inaccuracy' parameter defines the settling time the
        # sweeper should wait before changing a sweep parameter and recording the next
        # sweep data point. The settling time is calculated from the specified
        # proportion of a step response function that should remain. The value
        # provided here, 0.001, is appropriate for fast and reasonably accurate
        # amplitude measurements. For precise noise measurements it should be set to
        # ~100n.
        # Note: The actual time the sweeper waits before recording data is the maximum
        # time specified by sweep/settling/time and defined by
        # sweep/settling/inaccuracy.
        sweeper.set('sweep/settling/inaccuracy', 0.001)
        # Set the minimum time to record and average data to 10 demodulator
        # filter time constants.
        sweeper.set('sweep/averaging/tc', avgTCs)
        # Minimal number of samples that we want to record and average is 100. Note,
        # the number of samples used for averaging will be the maximum number of
        # samples specified by either sweep/averaging/tc or sweep/averaging/sample.
        sweeper.set('sweep/averaging/sample', 10)

        # Now subscribe to the nodes from which data will be recorded. Note, this is
        # not the subscribe from ziDAQServer; it is a Module subscribe. The Sweeper
        # Module needs to subscribe to the nodes it will return data for.x
        path = '/%s/demods/%d/sample' % (self.device_id, demod_index)
        sweeper.subscribe(path)

        # Start the Sweeper's thread.
        sweeper.execute()

        start = time.time()
        timeout = 2*(avgTCs + settleTCs)*time_constant*num_steps  # [s]
        print("Will perform", loopcount, "sweeps...")
        while not sweeper.finished():  # Wait until the sweep is complete, with timeout.
            time.sleep(0.2)
            progress = sweeper.progress()
            print("Individual sweep progress: {:.2%}.".format(progress[0]), end="\r")
            # Here we could read intermediate data via:
            # data = sweeper.read(True)...
            # and process it while the sweep is completing.
            # if device in data:
            # ...
            if (time.time() - start) > timeout:
                # If for some reason the sweep is blocking, force the end of the
                # measurement.
                print("\nSweep still not finished, forcing finish...")
                sweeper.finish()
        print("")

        # Read the sweep data. This command can also be executed whilst sweeping
        # (before finished() is True), in this case sweep data up to that time point
        # is returned. It's still necessary still need to issue read() at the end to
        # fetch the rest.
        return_flat_dict = True
        data = sweeper.read(return_flat_dict)
        sweeper.unsubscribe(path)

        # Stop the sweeper thread and clear the memory.
        sweeper.clear()

        # Check the dictionary returned is non-empty.
        assert data, "read() returned an empty data dictionary, did you subscribe to any paths?"
        # Note: data could be empty if no data arrived, e.g., if the demods were
        # disabled or had rate 0.
        assert path in data, "No sweep data in data dictionary: it has no key '%s'" % path
        samples = data[path]
        print("Returned sweeper data contains", len(samples), "sweeps.")
        assert len(samples) == loopcount, \
            "The sweeper returned an unexpected number of sweeps: `%d`. Expected: `%d`." % (len(samples), loopcount)

        if do_plot:
            import matplotlib.pyplot as plt
            plt.clf()
            for i in range(0, len(samples)):
                frequency = samples[i][0]['frequency']
                R = np.abs(samples[i][0]['x'] + 1j*samples[i][0]['y'])
                phi = np.angle(samples[i][0]['x'] + 1j*samples[i][0]['y'])
                plt.subplot(2, 1, 1)
                plt.semilogx(frequency, R)
                plt.subplot(2, 1, 2)
                plt.semilogx(frequency, phi)
            plt.subplot(2, 1, 1)
            plt.title('Results of %d sweeps.' % len(samples))
            plt.grid(True)
            plt.ylabel(r'Demodulator R ($V_\mathrm{RMS}$)')
            plt.ylim(0.0, 0.1)
            plt.subplot(2, 1, 2)
            plt.grid(True)
            plt.xlabel('Frequency ($Hz$)')
            plt.ylabel(r'Demodulator Phi (radians)')
            plt.autoscale()
            plt.draw()
            plt.show()

        return samples


    def aux_sweepND(self, auxchan, aux_stop, time = 5):
        """
        Sweeps the output of an aux channel from its current value to the
        chosen one. Returns no data.

        Arguments:

        aux_channel: number (1-4) of aux out to sweep.

        aux_stop: desired final aux voltage.

        time (optional): time over which to do the sweep. Will be slightly
                    more than this, depending on Zurich.

        """
        # Converts from 1 start to 0 start numerals.
        aux_channel = auxchan - 1

        # Disables all demods, scopes, sigouts. Enables demod 0.
        # Puts auxout 1 in manual mode (-1)
        general_setting = [['/%s/demods/*/enable' % self.device_id, 0],
                           ['/%s/demods/*/trigger' % self.device_id, 0],
                           ['/%s/sigouts/*/enables/*' % self.device_id, 0],
                           ['/%s/scopes/*/enable' % self.device_id, 0],
                           ['/%s/auxouts/%d/outputselect'  % (self.device_id, aux_channel),-1],
                           ['/%s/demods/0/enable'         % (self.device_id), 1],
                           ['/%s/demods/0/timeconstant'         % (self.device_id), 1e-9]]
        # Applies those settings.
        self.daq.set(general_setting)
        # Perform a global sync between the device and the data server.
        self.daq.sync()

        # Creates a sweeper object
        sweeperinitialize = self.daq.sweep()

        # Configure the Sweeper Module's parameters.

        # Set the device that will be used for the sweep, using class var.
        sweeperinitialize.set('sweep/device', self.device_id)

        # Specify the `gridnode`: The instrument node that we will sweep
        sweeperinitialize.set('sweep/gridnode', '/%s/auxouts/%d/offset' % (self.device_id,aux_channel))

        # Gets the current value of the chosen aux port
        current_aux_value =  self.daq.get(
                                '/%s/auxouts/%d/offset'
                                % (self.device_id,aux_channel))\
                                [self.device_id]['auxouts'][str(aux_channel)]\
                                ['offset'][0]
        # Determines if the sweep is up or down, as the sweeper only supports
        # start < stop.
        if current_aux_value <= aux_stop:
            # Sweep from start to stop
            sweeperinitialize.set('sweep/start', current_aux_value)
            sweeperinitialize.set('sweep/stop', aux_stop)
            # Sets scan type as monotonic increasing scan
            sweeperinitialize.set('sweep/scan', 0)
        else:
            # Scan from stop to start (since stop < start)
            sweeperinitialize.set('sweep/start', aux_stop)
            sweeperinitialize.set('sweep/stop', current_aux_value)
            # But scan backwards
            sweeperinitialize.set('sweep/scan', 3)
        num_steps = 100
        # Set number of steps
        sweeperinitialize.set('sweep/samplecount', num_steps)
        # Specify linear spacing
        sweeperinitialize.set('sweep/xmapping', 0)
        # Turn off bandwidth control.
        sweeperinitialize.set('sweep/bandwidthcontrol', 0)
        # Disable bandwidth overlap.
        sweeperinitialize.set('sweep/bandwidthoverlap', 0)
        # Do exactly one loop.
        sweeperinitialize.set('sweep/loopcount', 1)
        # Set the time to sit at each point
        sweeperinitialize.set('sweep/settling/time', time/num_steps)
        # Turn off inaccuracy control
        sweeperinitialize.set('sweep/settling/inaccuracy', 0)
        # Average for 0 tcs
        sweeperinitialize.set('sweep/averaging/tc', 0)
        # Average for 0 samples
        sweeperinitialize.set('sweep/averaging/sample', 0)
        # Even though we don't want the data, subscribing is required for
        # checking if the sweeper is finished.
        path = '/%s/demods/0/sample' % self.device_id
        sweeperinitialize.subscribe(path)
        # Start the sweep
        sweeperinitialize.execute()

        # Pause evaluation while sweep runs
        while not sweeperinitialize.finished():
            pass

        #Unsubscribe and clear sweeper
        sweeperinitialize.unsubscribe(path)
        sweeperinitialize.clear()

    def aux_sweep(self, aux_start, aux_stop, num_steps, time_constant = 1e-3,
                 amplitude = .01, freq = 200,  auxchan = 1, outputchan = 1, inputchan = 1,
                 couple = 'dc', settleTCs = 10, avgTCs = 5, loopcount = 1,
                 gatesweep = False, keithley = False, compliance = 1E-9, ta_gain = 1e8):
        """
        Sweeps the output of an aux channel, while recording chosen input.
        If the goal is to do a DC biased lock in measurement (i.e. AC Rds vs
        Vds), auxchan should be connected to "add" of outputchan. Additionally
        has the ability to do the measurement multiple times with different
        voltages on a passed Keithley 2400.

        Citation: Adapted from Zurich Instruments' "sweep" example.

        Arguments:

          aux_start (float): start voltage of the sweep in volts

          aux_stop (float): stop voltage of the sweep in volts. Must be
                    greater than start voltage.

          num_steps (int): number of frequency steps to perform

          time_constant (float, optional): demod timeconstant

          amplitude (float, optional): The amplitude to set on the signal output.

          freq (float, optional): the frequency of the lock in measurement. If
              ac couple is enabled (not default), it must be greater than 100 hz
              (corner of ac highpass).

          auxchan (int, optional): input channel (1 or 2)

          outputchan (int, optional): output channel (1 or 2)

          inputchan (int, optional): input channel (1 or 2). In nearly all
            applications, outputchan = inputchan.

          couple (string, optional): ac couple if str = 'ac', o.w. dc couple

          settleTCs (int, optional): number of time constants to allow demod to
            stabilize after sweep.

          avgTCs (int, optional): number of time constants to average demod
            output for data point.

          loopcount (int, optional): how many of each sweep to do. Default
            is one.

          gatesweep (list, optional): list of gate voltages to do sweep at.
            Requires a keithley class to be passed. Default is False, no
            gatesweep.

          keithley (class, optional): keithley class object to control
            backgate. For safety reasons, must be handed to function with
            it's output enabled. Default: False, no gatesweep.

          compliance (float, optional): compliance to use for sweeping gate.
            for safety reasons, it is reset by this method. Default: 1 nA

          ta_gain (int): gain of Zurich HF2TA transimpedence amplifier.
            HF2TA must be configured in LabOne, this value allows plots to
            have correct y-axis.

        Returns:

          sample (list of dict): A list of demodulator sample dictionaries. Each
            entry in the list correspond to the result of a single sweep and is a
            dict containing a demodulator sample.

        """


        # Create a base instrument configuration: disable all outputs, demods and scopes.
        general_setting = [['/%s/demods/*/enable' % self.device_id, 0],
                           ['/%s/demods/*/trigger' % self.device_id, 0],
                           ['/%s/sigouts/*/enables/*' % self.device_id, 0],
                           ['/%s/scopes/*/enable' % self.device_id, 0]]
        self.daq.set(general_setting)
        # Performs a global sync between the device and the data server
        self.daq.sync()

        # Calculate start 0 numbers for channels
        out_channel = outputchan - 1
        in_channel = inputchan - 1
        aux_channel = auxchan - 1
        # Uses demod 0 by default.
        demod_index = 0
        # Uses the osc corresponding to the input channel.
        osc_index = in_channel
        # Detects the correct mixer channel.
        out_mixer_channel = int(self.daq.listNodes('/%s/sigouts/%d/amplitudes/'
                                    % (self.device_id, out_channel),0)[0])
        # Sets the demod communication rate
        demod_rate = 10e3
        # Determine whether the user wants ac or dc couple
        if couple == 'ac':
            # AC couple
            acUse = 1
        else:
            # Disable AC couple (use DC couple)
            acUse = 0

        # Sets up the experiment. Please excuse the long line length,
        # I relax PEP8 here for clarity.
        exp_setting = [['/%s/sigins/%d/ac'             % (self.device_id, in_channel), acUse],
                       ['/%s/sigins/%d/range'          % (self.device_id, in_channel), 2],
                       ['/%s/sigins/%d/diff'           % (self.device_id, in_channel), 0],
                       ['/%s/demods/%d/enable'         % (self.device_id, demod_index), 1],
                       ['/%s/demods/%d/rate'           % (self.device_id, demod_index), demod_rate],
                       ['/%s/demods/%d/adcselect'      % (self.device_id, demod_index), in_channel],
                       ['/%s/demods/%d/order'          % (self.device_id, demod_index), 4],
                       ['/%s/demods/%d/timeconstant'   % (self.device_id, demod_index), time_constant],
                       ['/%s/demods/%d/oscselect'      % (self.device_id, demod_index), osc_index],
                       ['/%s/demods/%d/harmonic'       % (self.device_id, demod_index), 1],
                       ['/%s/sigouts/%d/on'            % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/enables/%d'    % (self.device_id, out_channel, out_mixer_channel), 1],
                       ['/%s/oscs/%d/freq'             % (self.device_id, out_channel), freq],
                       ['/%s/sigouts/%d/range'         % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/add'           % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/amplitudes/%d' % (self.device_id, out_channel, out_mixer_channel), amplitude],
                       ['/%s/auxouts/%d/outputselect'  % (self.device_id, aux_channel),-1]
                      ]

        #Sets settings to ZI
        self.daq.set(exp_setting)

        # Create empty dict in which to put data.
        data = {}

        # Outer most try-except detects if during initial ramp up to
        # the current gate value, the gate fails. Stops the iterative loop
        # over gate values and reports to the user.
        try:
            # while True ... if (..) break structure to impliment do...while
            # in Python. Iterates over gate voltages.
            while True:
                # Checks if gatesweep has values in it, and Keithley is not
                # false.
                if  gatesweep and keithley:
                    # Sets keithley to compliance
                    keithley.I_compliance = compliance
                    # pops first gatevalue, removing it and returning it
                    current_gate = gatesweep.pop(0)
                    # sets keithley to that gate value, compliance ensuring
                    # a slow ramp.
                    keithley.Vout = current_gate
                    # check start time for timeout
                    start_time = time.time()
                    # waits for current to drop below 90% of compliance.
                    while abs(keithley.I) > .9*compliance:
                        # checks for timeout, throws error to try if
                        # timeout occurs.
                        if time.time() - start_time > 240:
                            print("Could not reach requested gate voltage")
                            raise gateVoltageError
                # if either is false, then the gate sweep is disabled.
                else:
                    current_gate = 'nogatesweep'

                # 1 second pause for things to stabilize
                time.sleep(1)

                # Sweeps auxchan from its current value to the requested
                # start value.
                self.aux_sweepND(auxchan,aux_start)

                # configures a sweeper.
                sweeper = self.daq.sweep()
                # Configure the Sweeper Module's parameters.
                # Set the device that will be used for the sweep
                sweeper.set('sweep/device', self.device_id)
                # Specify the `gridnode`: The node that we will sweep
                sweeper.set('sweep/gridnode', '/%s/auxouts/%d/offset'
                                                % (self.device_id,aux_channel))
                # Set the `start` and `stop` values
                sweeper.set('sweep/start', aux_start)
                sweeper.set('sweep/stop', aux_stop)
                # Set the number of points to use for the sweep
                sweeper.set('sweep/samplecount', num_steps)
                # Linear spacing
                sweeper.set('sweep/xmapping', 0)
                # Turn off bandwidth control
                sweeper.set('sweep/bandwidthcontrol', 0)
                # Turn off bandwidth overlap control
                sweeper.set('sweep/bandwidthoverlap', 0)
                # Sequential scan mode (0)
                sweeper.set('sweep/scan', 0)
                # Specify the number of sweeps to perform back-to-back.
                sweeper.set('sweep/loopcount', loopcount)
                # Set the settling time.
                sweeper.set('sweep/settling/time', settleTCs*time_constant)
                # Set the inaccuracy allowed as a coarse emergency backup for
                # the chosen settling time. Inaccuracy cannot be worse than
                # 1 percent, ever.
                sweeper.set('sweep/settling/inaccuracy', 0.01)
                # Average for avgTCs time constants.
                sweeper.set('sweep/averaging/tc', avgTCs)
                # We do our averaging by tc specifications, not samples. Set
                # to 1.
                sweeper.set('sweep/averaging/sample', 1)

                # Now subscribe to the nodes from which data will be recorded.
                # Note, this is not the subscribe from ziDAQServer;
                # it is a Module subscribe. The Sweeper Module needs to
                # subscribe to the nodes it will return data for.
                path = '/%s/demods/%d/sample' % (self.device_id, demod_index)
                sweeper.subscribe(path)
                # Start the Sweeper's thread.
                sweeper.execute()
                # record start time for timeout purposes.
                start = time.time()
                # Calculates maximum allowed time
                timeout = 2*(avgTCs + settleTCs)*time_constant*num_steps + 10  # [s]
                # Informs the user where it is in the sweep, if there is a
                # gate sweep
                if current_gate != 'nogatesweep':
                    print("Current gate voltage: ", current_gate, "V   Voltages Remaining:",
                            len(gatesweep))
                # Suspends evaluation while the sweeper runs
                while not sweeper.finished():
                    # Wait until the sweep is complete, with timeout.
                    # Keeps loop from interrogating zurich too much
                    # and slowing things down.
                    time.sleep(0.2)

                    # checks timout
                    if (time.time() - start) > timeout:
                        # tells user about timeout
                        print("\nSweep still not finished, forcing finish...")
                        # forces sweeper to finish
                        sweeper.finish()
                        # checks if keithley is enabled, and if gate
                        # voltage is more than .1 away from correct
                    if (bool(keithley)
                        and abs(keithley.Vout - current_gate) > .1):
                        # raises gatevoltageerror and tells user.
                        print("Gate voltage could not be maintained, forcing finish...")
                        sweeper.finish()
                        sweeper.clear()
                        raise gateVoltageError

                # Return flat dictionary.
                return_flat_dict = True
                # Return data from zurich
                data[str(current_gate)] = sweeper.read(return_flat_dict)
                # Unsubscribe from path
                sweeper.unsubscribe(path)
                # Stop the sweeper thread and clear the memory.
                sweeper.clear()
                # if either gatesweep is empty or false, break out of
                # gatesweep loop.
                if not gatesweep:
                    break
        # handle gateVoltageError, just pass since sweeper finished and clear
        # in loop
        except gateVoltageError:
            pass
        # handle keyboardinterrupts so that data is still returned
        except KeyboardInterrupt:
            # try to quit sweeper, may not exist.
            try:
                 sweeper.finish()
                 sweeper.unsubscribe(path)
                 sweeper.clear()
            except:
                pass
        # Flatten dict
        for i in data.keys():
            samples[i] = data[i][path]
        # Ramp keithley to zero, if it exists
        if keithley:
            keithley.I_compliance = 1e-9
            keithley.Vout = 0
            while abs(keithley.I) > .9*compliance:
                pass
        # Ramp aux down safely.
        self.aux_sweepND(auxchan,0)
        # if samples is non-empty, plot
        if samples:
            import matplotlib.pyplot as plt
            # clear figure
            plt.clf()
            # for each gate value, create a plot trace
            for gate in samples.keys():
                # set vds to the "grid" node, that is, the swept variable
                vds = samples[gate][0][0]['grid']
                # set y axis to the calculated conductivity. Uses passed
                # ta_gain and amplitude
                R = np.abs((samples[gate][0][0]['x'] + 1j*samples[gate][0][0]['y'])
                            *1/(ta_gain  * amplitude)*1e9)
                plt.plot(vds, R, label = 'Gate %s V' % gate)
            # Get the current axis
            ax = plt.gca()
            # plot legend outside plot
            plt.legend(bbox_to_anchor=(1.4, 1.0))
            # turn on grid, for Brian
            plt.grid(True)
            # label axes
            plt.ylabel(r'Conductivity DS (nA/V)')
            plt.xlabel('$V_\mathrm{ds}$ bias ($V$)')
            # show plot without returning.
            plt.draw()
            plt.show()
        return samples