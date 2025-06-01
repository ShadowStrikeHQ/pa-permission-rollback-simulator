import argparse
import logging
import os
import sys
from typing import List, Dict, Set, Tuple

import networkx as nx
from pathspec import PathSpec
from rich.console import Console
from rich.table import Column, Table

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PermissionRollbackSimulator:
    """
    Simulates the impact of permission rollbacks on a file system.
    """

    def __init__(self, file_system_data: Dict[str, List[str]]):
        """
        Initializes the simulator with file system data.

        Args:
            file_system_data (Dict[str, List[str]]): A dictionary representing the file system.
                Keys are file/directory paths, and values are lists of users/groups with access.
        """
        self.file_system_data = file_system_data
        self.graph = nx.DiGraph()  # Directed graph to represent dependencies
        self.console = Console()

    def build_dependency_graph(self):
        """
        Builds a directed graph representing file system dependencies.
        Nodes are files/directories, and edges represent access relationships.
        """
        try:
            for path, permissions in self.file_system_data.items():
                self.graph.add_node(path)
                for user in permissions:
                    # Consider 'user' as having access to 'path'
                    self.graph.add_edge(user, path) # Edge from user to the resource they have access to
        except Exception as e:
            logging.error(f"Error building dependency graph: {e}")
            raise

    def simulate_rollback(self, target_user: str) -> Tuple[Set[str], Set[str]]:
        """
        Simulates the removal of permissions for a target user.

        Args:
            target_user (str): The user whose permissions are being rolled back.

        Returns:
            Tuple[Set[str], Set[str]]: A tuple containing two sets:
                - impacted_resources: Resources that are directly impacted by the rollback.
                - indirectly_impacted_resources: Resources indirectly impacted (through dependencies).
        """
        try:
            impacted_resources = set()
            indirectly_impacted_resources = set()

            # 1. Identify directly impacted resources
            for u, v in self.graph.edges():
                if u == target_user:
                    impacted_resources.add(v)
            
            # Simulate removing edges related to target user
            edges_to_remove = [(u, v) for u, v in self.graph.edges() if u == target_user]
            self.graph.remove_edges_from(edges_to_remove)

            # 2. Identify indirectly impacted resources (resources no longer accessible)
            # This requires more sophisticated dependency analysis.  For now,
            # we'll consider resources that are no longer reachable from any user.
            accessible_resources = set()
            for node in self.graph.nodes():
                if isinstance(node, str) and node in self.file_system_data.keys(): #Check that it's a resource
                    for user in self.file_system_data[node]: #For each user, check reachability
                        try:
                            for path in nx.descendants(self.graph, user): #Find the paths accessible to each user
                                accessible_resources.add(path)
                        except nx.NetworkXError as e:
                            #Node not in the graph
                            pass
            indirectly_impacted_resources = set(self.file_system_data.keys()) - accessible_resources
            
            return impacted_resources, indirectly_impacted_resources

        except Exception as e:
            logging.error(f"Error simulating rollback: {e}")
            raise

    def display_results(self, impacted_resources: Set[str], indirectly_impacted_resources: Set[str]):
        """
        Displays the results of the rollback simulation using rich.

        Args:
            impacted_resources (Set[str]): Set of resources directly impacted.
            indirectly_impacted_resources (Set[str]): Set of resources indirectly impacted.
        """
        table = Table(title="Permission Rollback Simulation Results")
        table.add_column("Impact Type", style="cyan", no_wrap=True)
        table.add_column("Resource", style="magenta")

        for resource in sorted(impacted_resources):
            table.add_row("Directly Impacted", resource)

        for resource in sorted(indirectly_impacted_resources):
            table.add_row("Indirectly Impacted", resource)

        self.console.print(table)

def setup_argparse() -> argparse.ArgumentParser:
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Simulates the impact of permission rollbacks on a file system."
    )
    parser.add_argument(
        "--user",
        type=str,
        required=True,
        help="The user whose permissions are being rolled back.",
    )
    parser.add_argument(
        "--data_file",
        type=str,
        required=True,
        help="Path to a JSON file containing file system data (permissions).",
    )
    return parser


def main():
    """
    Main function to execute the permission rollback simulator.
    """
    try:
        parser = setup_argparse()
        args = parser.parse_args()

        # Input validation
        if not os.path.exists(args.data_file):
            logging.error(f"Data file not found: {args.data_file}")
            print(f"Error: Data file not found: {args.data_file}")
            sys.exit(1)

        # Load file system data from the JSON file
        try:
            import json
            with open(args.data_file, 'r') as f:
                file_system_data = json.load(f)
                # Validate that the data is a dictionary
                if not isinstance(file_system_data, dict):
                    logging.error("Data file must contain a dictionary.")
                    print("Error: Data file must contain a dictionary.")
                    sys.exit(1)
                # Validate that the dictionary contains lists of strings
                for k, v in file_system_data.items():
                    if not isinstance(v, list):
                        logging.error("Values in data file dictionary must be lists.")
                        print("Error: Values in data file dictionary must be lists.")
                        sys.exit(1)
                    for item in v:
                        if not isinstance(item, str):
                            logging.error("List values in data file must be strings.")
                            print("Error: List values in data file must be strings.")
                            sys.exit(1)

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON file: {e}")
            print(f"Error decoding JSON file: {e}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error loading file system data: {e}")
            print(f"Error loading file system data: {e}")
            sys.exit(1)


        simulator = PermissionRollbackSimulator(file_system_data)
        simulator.build_dependency_graph()
        impacted_resources, indirectly_impacted_resources = simulator.simulate_rollback(args.user)
        simulator.display_results(impacted_resources, indirectly_impacted_resources)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()