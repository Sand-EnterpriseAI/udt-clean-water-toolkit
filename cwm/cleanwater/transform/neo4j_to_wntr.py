import pandas as pd
import numpy as np
import wntr


class Neo4j2Wntr:
    """
    Convert a Neo4j graph to Water Network Toolkit (WNTR) format.

    This class is responsible for converting graph data from a Neo4j database
    into a format compatible with the Water Network Toolkit (WNTR) for hydraulic
    and water network analysis. It includes methods for setting up simulation
    parameters, adding nodes and pipes, generating demand patterns, and running
    simulations.

    Parameters:
        config: Configuration object containing settings for the conversion.
    """

    def __init__(self, config):
        """
        Initialize the Neo4j2Wntr class.

        Parameters:
            config: Configuration object containing settings for the conversion.
        """
        self.config = config  # Store configuration settings.
        self.inpfile = self.config.inpfile  # Path to the INP file if applicable.
        self.wn = wntr.network.WaterNetworkModel()  # Initialize a new WNTR network model.

        # Set default hydraulic options
        self.set_hydraulic_options()

        # Set simulation time options
        self.set_simulation_time_options()

    def set_simulation_time_options(self):
        """
        Set the time-related simulation options for the WNTR model.

        This method configures the simulation duration, hydraulic timestep, pattern
        timestep, and report timestep based on the configuration settings.
        """
        self.wn.options.time.duration = self.config.wntr_simulation_length_hours * 3600
        self.wn.options.time.hydraulic_timestep = self.config.wntr_simulation_timestep_hours * 3600
        self.wn.options.time.pattern_timestep = self.config.wntr_simulation_timestep_hours * 3600
        self.wn.options.time.report_timestep = self.config.wntr_simulation_timestep_hours * 3600

    def set_hydraulic_options(self):
        """
        Set the hydraulic options for the WNTR model.

        This method configures the hydraulic options such as the demand model,
        accuracy, headloss method, and other parameters.
        """
        self.wn.options.hydraulic.demand_model = 'DDA'  # Demand model: DDA (Draft Demand Analysis)
        self.wn.options.hydraulic.accuracy = 0.001  # Accuracy of hydraulic calculations
        self.wn.options.hydraulic.headloss = 'H-W'  # Headloss method: Hazen-Williams
        self.wn.options.hydraulic.minimum_pressure = 0.0  # Minimum pressure allowed
        self.wn.options.hydraulic.required_pressure = 0.07  # Required pressure
        self.wn.options.hydraulic.pressure_exponent = 0.5  # Pressure exponent for headloss calculation
        self.wn.options.hydraulic.emitter_exponent = 0.5  # Emitter exponent for demand calculations
        self.wn.options.hydraulic.trials = 200  # Number of trials for hydraulic solutions
        self.wn.options.hydraulic.unbalanced = 'STOP'  # Action to take if unbalanced solution is detected
        self.wn.options.hydraulic.checkfreq = 2  # Frequency of hydraulic checks
        self.wn.options.hydraulic.maxcheck = 10  # Maximum number of hydraulic checks
        self.wn.options.hydraulic.damplimit = 0.0  # Damping limit for convergence
        self.wn.options.hydraulic.headerror = 0.0  # Head error tolerance
        self.wn.options.hydraulic.flowchange = 0.0  # Flow change tolerance
        self.wn.options.hydraulic.inpfile_units = 'LPS'  # Units for input file: Liters per second
        self.wn.options.hydraulic.inpfile_pressure_units = 'LPS'  # Units for pressure in input file

    def set_reaction_options(self):
        """
        Set the reaction-related options for the WNTR model.

        This method configures the reaction kinetics parameters including bulk
        and wall order, coefficients, and other related settings.
        """
        self.wn.options.reaction.bulk_order = 1.0  # Order of bulk reaction kinetics
        self.wn.options.reaction.wall_order = 1.0  # Order of wall reaction kinetics
        self.wn.options.reaction.tank_order = 1.0  # Order of tank reaction kinetics
        self.wn.options.reaction.bulk_coeff = 0.0  # Bulk reaction coefficient
        self.wn.options.reaction.wall_coeff = 0.0  # Wall reaction coefficient
        self.wn.options.reaction.limiting_potential = None  # Limiting potential for reaction
        self.wn.options.reaction.roughness_correl = None  # Roughness correlation for reaction

    @staticmethod
    def convert_coords(coords):
        """
        Helper function to convert coordinates to a tuple.

        Parameters:
            coords: Coordinates in a list format.

        Returns:
            tuple: Coordinates as a tuple.
        """
        return tuple(coords)

    def flatten_list(self, nested_list):
        """
        Flatten a nested list into a single list.

        Parameters:
            nested_list: A potentially nested list to flatten.

        Returns:
            list: A flattened list containing all elements.
        """
        flattened_list = []
        for item in nested_list:
            if isinstance(item, list):
                flattened_list.extend(self.flatten_list(item))
            else:
                flattened_list.append(item)
        return flattened_list

    @staticmethod
    def generate_random_value(min_value, max_value):
        """
        Generate a random value within the specified range.

        Parameters:
            min_value (float): Minimum value for the random number.
            max_value (float): Maximum value for the random number.

        Returns:
            float: A random value within the specified range.
        """
        return np.random.uniform(min_value, max_value)

    def add_node(self, node_id_str, coordinates, node_type):
        """
        Adds a node to the water network model based on its type.

        Parameters:
            node_id_str (str): ID of the node.
            coordinates (tuple): Coordinates of the node.
            node_type (list): List of asset labels associated with the node.
        """
        if node_type:
            is_meter = [item for item in node_type if item.endswith('Meter')]
            if is_meter:
                self.add_consumption_junction(node_id_str, coordinates)
            elif "reservoir" in node_type:
                self.add_reservoir(node_id_str, coordinates)
            else:
                self.add_junction(node_id_str, coordinates)
        else:
            self.add_junction(node_id_str, coordinates)

    def add_junction(self, node_id_str, coordinates):
        """
        Adds a non-consumption junction to the network.

        Parameters:
            node_id_str (str): ID of the node.
            coordinates (tuple): Coordinates of the node.
        """
        elevation = self.generate_random_value(20, 40)  # Example elevation range
        base_demand = 0  # Non-consumption junction
        self.wn.add_junction(node_id_str,
                             elevation=elevation,
                             base_demand=base_demand,
                             coordinates=coordinates)

    def add_reservoir(self, node_id_str, coordinates):
        """
        Adds a reservoir to the network.

        Parameters:
            node_id_str (str): ID of the reservoir.
            coordinates (tuple): Coordinates of the reservoir.
        """
        base_head = 20.0  # Example base head
        self.wn.add_reservoir(node_id_str, base_head=base_head, coordinates=coordinates)

    def add_pipe(self, edge_id, start_node_id, end_node_id, diameter, length, roughness):
        """
        Adds a pipe to the water network model.

        Parameters:
            edge_id (str): ID of the pipe.
            start_node_id (str): ID of the start node.
            end_node_id (str): ID of the end node.
            diameter (float): Diameter of the pipe.
            length (float): Length of the pipe.
            roughness (float): Roughness coefficient of the pipe.
        """
        self.wn.add_pipe(
            edge_id,
            start_node_id,
            end_node_id,
            length=length,
            diameter=diameter,
            roughness=roughness
        )

    def add_consumption_junction(self, node_id_str, coordinates):
        """
        Adds a consumption junction to the network and assigns a demand pattern.

        Parameters:
            node_id_str (str): ID of the junction.
            coordinates (tuple): Coordinates of the junction.
        """
        elevation = self.generate_random_value(20, 40)  # Example elevation range
        base_demand = self.generate_random_value(10, 50)  # Example demand range
        self.wn.add_junction(node_id_str,
                             elevation=elevation,
                             base_demand=base_demand,
                             coordinates=coordinates)

        # Generate and assign a daily demand pattern
        self.assign_demand_pattern(node_id_str)

    def generate_daily_pattern(self, peak_factor=1.5):
        """
        Generate a daily demand pattern with a given time interval.

        Parameters:
            peak_factor (float): Factor to adjust the peak demand.

        Returns:
            pattern (list): A list of demand factors for each time interval.
        """
        # Number of time steps in a day
        num_steps = int(self.config.wntr_simulation_length_hours / self.config.wntr_simulation_timestep_hours)

        # Create a base pattern with typical daily usage
        base_pattern = np.sin(np.linspace(0, 2 * np.pi, num_steps)) + 1.1  # Sinusoidal pattern with daily peak

        # Normalize to sum to 1 and then scale to typical daily demand (e.g., total demand for a node)
        base_pattern = (base_pattern - np.min(base_pattern)) / (np.max(base_pattern) - np.min(base_pattern))

        # Scale the pattern to include peak demand
        pattern = base_pattern * peak_factor

        return pattern.tolist()

    def assign_demand_pattern(self, node_id_str):
        """
        Create and assign a daily demand pattern to a specific consumption junction.

        Parameters:
            node_id_str (str): The ID of the node to which the pattern will be assigned.
        """
        # Generate the pattern
        pattern_values = self.generate_daily_pattern()
        pattern_name = 'daily_pattern_' + node_id_str

        # Add the pattern to the network model
        self.wn.add_pattern(name=pattern_name, pattern=pattern_values)

        # Create a TimeSeries object with the pattern
        demand_base_value = self.wn.get_node(node_id_str).base_demand

        # Assign the TimeSeries object to the node's demand_timeseries_list
        for demand in self.wn.get_node(node_id_str).demand_timeseries_list:
            demand.base_value = demand_base_value
            demand.pattern_name = pattern_name

    def load_inp(self):
        """
        Load an existing INP file into the WNTR model.

        This method initializes the WNTR model with an existing INP file specified in
        the configuration.
        """
        self.wn = wntr.network.WaterNetworkModel(self.inpfile)

    def run_hydraulic_sim(self):
        """
        Run a hydraulic simulation on the WNTR model and save the results to a CSV file.

        This method performs a hydraulic simulation using the WNTR simulator, then
        processes the results to include time steps and saves them in a CSV format.
        """
        sim = wntr.sim.WNTRSimulator(self.wn)  # Initialize the WNTR simulator
        results_WNTR = sim.run_sim()  # Run the simulation
        flow_results = results_WNTR.link['flowrate']  # Extract flow results

        # Get the time step information
        duration = self.wn.options.time.duration
        hydraulic_timestep = self.wn.options.time.hydraulic_timestep

        # Calculate the time steps
        time_steps = pd.date_range(start='0:00:00', periods=int(duration / hydraulic_timestep) + 1,
                                   freq=f'{hydraulic_timestep}s')

        # Convert time_steps to a dataframe
        time_steps_df = pd.DataFrame({'Time': time_steps})

        # Add the time steps to the flow results
        flow_results_with_time = pd.concat([time_steps_df, flow_results.reset_index(drop=True)], axis=1)

        # Prepare the header for the CSV
        flow_results_with_time.columns = ['Time'] + [f'{link_id}' for link_id in flow_results.columns]
        flow_results_with_time.to_csv('flowrates.csv', index=False)

        # Read the CSV file to add the top-left header
        df = pd.read_csv('flowrates.csv')
        df.columns.values[0] = 'Time steps'
        df.to_csv('flowrates.csv', index=False)

    def check_graph_completeness(self):
        self.keep_largest_component()
        node_ids_queried = [str(node._id) for node in self.nodes_loaded]
        node_ids_added = self.wn.node_name_list
        missing_nodes = set(node_ids_queried) - set(node_ids_added)
        if missing_nodes:
            print(f"{len(missing_nodes)} nodes excluded from final model")
        else:
            print("All queried nodes added to WN")

        link_ids_queried = [str(link._id) for link in self.links_loaded]
        link_ids_added = self.wn.link_name_list
        missing_links = set(link_ids_queried) - set(link_ids_added)
        if missing_links:
            print(f"{len(missing_links)} links excluded from final model")
        else:
            print("All queried edges added to WN")

    def keep_largest_component(self):
        # Create an undirected graph from the water network model
        G = self.wn.to_graph().to_undirected()

        # Find all connected components
        connected_components = list(nx.connected_components(G))

        # Identify the largest connected component
        largest_component = max(connected_components, key=len)

        # Find nodes to remove
        nodes_to_remove = set(G.nodes()) - largest_component

        # Find links to remove (links connected to nodes_to_remove)
        links_to_remove = []
        for link_name, link in self.wn.links():
            if link.start_node_name in nodes_to_remove or link.end_node_name in nodes_to_remove:
                links_to_remove.append(link_name)

        # Remove links from the water network model
        for link_name in links_to_remove:
            self.wn.remove_link(link_name)

        # Remove nodes from the water network model
        for node_name in nodes_to_remove:
            self.wn.remove_node(node_name)
