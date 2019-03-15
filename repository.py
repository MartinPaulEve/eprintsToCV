import os

import requests
import json


class Repository:
    def __init__(self, config, logger, refresh):
        """
        Initialise a repository
        :param config: a configuration
        :param logger: a logger
        :param refresh: whether fetch operations should hit the remote endpoint even if there is an on-disk copy
        """
        self.config = config
        self.logger = logger
        self.url = self._build_repo_url()
        self.json = None
        self._json_loaded = False
        self.refresh = refresh
        self._type_safe = False

    def __getattr__(self, name):
        """
        A generic getter for undefined attributes that we use to return types (e.g. repo.book_sections)
        :param name: the name of the attr
        """
        try:
            with open(self.config.storage[name], "r") as json_in_file:
                data = json_in_file.readlines()
                output = []
                for line in data:
                    output.append(json.loads(line))
                return output
        except EnvironmentError:
            self.logger.error('Cannot load json from {0}'.format(self.config.storage[name]))
            return None

    def _build_repo_url(self):
        """
        Creates the eprints endpoint URL
        :return: an eprints endpoint URL string
        """
        # build the repository path
        repo = self.config.eprints['repo']

        if not (repo.startswith("htt")):
            repo = "https://" + repo

        if not (repo.endswith("/")):
            repo += "/"

        url = repo + "cgi/exportview/people/" + self.config.eprints['user'] + "/JSON/"
        url += self.config.eprints['user'] + ".js"

        self.logger.debug('Built repository URL as: {0}'.format(url))

        return url

    def _populate_json(self, refresh):
        """
        Updates the internal json object either from the on-disk file or from the remote repo
        :param refresh: whether to refresh the remote repository even if there is an on-disk representation
        :return: boolean indicating whether the operation succeeded
        """

        # determine whether to refresh the JSON
        if not os.path.isfile(self.config.storage["json"]) and not refresh:
            self.logger.debug("Attempting to refresh {0}".format(self.url))

            try:
                # download the JSON
                data = requests.get(self.url).text
            except requests.RequestException as exc:
                self.logger.error("Error fetching eprints data: {0}".format(exc))
                self._json_loaded = False
                return False

            try:
                # write the JSON to the output file
                with open(self.config.storage["json"], "w") as json_out_file:
                    json_out_file.write(data)
                    self.json = json.loads(data)
                    self._json_loaded = True
                    return True
            except EnvironmentError:
                self.logger.error('Cannot write json data to {0}'.format(self.config.storage["json"]))
                # try to delete the file
                os.remove(self.config.storage["json"])
                self._json_loaded = False
                return False
        else:
            # load the JSON from the disk instead
            self.logger.debug("Attempting to load JSON from data store {0}".format(self.config.storage["json"]))
            try:
                with open(self.config.storage["json"], "r") as json_in_file:
                    data = json_in_file.read()
                    self.json = json.loads(data)
                    self._json_loaded = True
                    return True
            except EnvironmentError:
                self.logger.error('Cannot load json from {0}'.format(self.config.storage["json"]))
                self._json_loaded = False
                return False

    def _parse_json(self, types, load_json=False, check_types=False):
        """
        Parse JSON from eprints into sections
        :param types: the types to parse
        :param load_json: whether this function should attempt to load the JSON from the repo
        :param check_types: whether this function should attempt to check type validity
        :return: True if successful, otherwise False
        """
        self.logger.debug("Attempting to parse types {0}".format(types))

        # perform the prechecks
        if not self._parse_prechecks(check_types, load_json, types):
            return False

        # build a dictionary of output types with items in them
        self.logger.debug("Building output list")
        outputs = self._build_output_types_list()

        return self._write_sections_to_disk(outputs)

    def _write_sections_to_disk(self, outputs):
        """
        Writes the outputs to the disk for fast access
        :param outputs: the outputs to write
        :return: True if success, otherwise False
        """
        for output_type, output_list in outputs.items():
            self.logger.debug("Writing {0} to {1}".format(output_type, self.config.storage[output_type]))
            try:
                # write the JSON to the output file
                with open(self.config.storage[output_type], "w") as json_out_file:
                    for output in output_list:
                        json_out_file.write(json.dumps(output) + '\n')
            except EnvironmentError:
                self.logger.error('Cannot write json data to {0}'.format(self.config.storage["json"]))
                # try to delete the file
                os.remove(self.config.storage[output_type])
                self._json_loaded = False
                return False
        return True

    def _build_output_types_list(self):
        """
        Build a dictionary of output types with corresponding outputs within
        :return: a dictionary of output types as keys with corresponding outputs within
        """
        outputs = {}

        eprints_db_vals = list(self.config.eprints_db.values())

        for item in self.json:
            if item['type'] in eprints_db_vals:
                # this is an item that we need to handle

                # do a naughty reverse dictionary lookup of all types that correspond
                potential_types = self._get_potential_types(item)

                # reduce the types according to the allowed peer review criteria
                potential_types = self._filter_by_peer_review(item, potential_types)

                # reduce the types according to the allowed edited criteria
                potential_types = self._filter_by_editorial(item, potential_types)

                # reduce the types according to the allowed book review criteria
                potential_types = self._filter_by_book_review(item, potential_types)

                # we now have a list of types to add to the output dictionary
                for remaining_type in potential_types:
                    if remaining_type not in outputs:
                        self.logger.debug("Adding type {0} to outputs for the first time".format(remaining_type))
                        outputs[remaining_type] = []

                    outputs[remaining_type].append(item)
            else:
                self.logger.debug("Unsure how to handle type {0} for item {1}".format(item['type'], item['title']))

        return outputs

    def _filter_by_book_review(self, item, potential_types):
        """
        Reduces an item type list by its book review criteria
        :param item: the item
        :param potential_types: a list of potential types for the item
        :return: a list of filtered potential types
        """
        filtered_types = []

        for potential_type in potential_types:
            # determine whether the potential type matches the review criteria
            if self.config.book_review[potential_type] == 'ANY':
                # this type allows both book review and non-book-review items
                filtered_types.append(potential_type)

            elif self.config.book_review[potential_type] and item['title'].startswith("Review of"):
                # this type allows only book reviews
                filtered_types.append(potential_type)

            elif not self.config.book_review[potential_type] and item['title'].startswith("Review of") == False:
                # this type allows only non-book-reviews
                filtered_types.append(potential_type)

        self.logger.debug("Reduced types for {0} to {1}".format(item['title'], filtered_types))
        return filtered_types

    def _filter_by_editorial(self, item, potential_types):
        """
        Reduces an item type list by its editorial criteria
        :param item: the item
        :param potential_types: a list of potential types for the item
        :return: a list of filtered potential types
        """
        filtered_types = []

        for potential_type in potential_types:
            # determine whether the potential type matches the review criteria
            if self.config.editorial[potential_type] == 'ANY':
                # this type allows both edited and non-edited items
                filtered_types.append(potential_type)

            elif self.config.editorial[potential_type] and 'editors' in item:
                # this type allows only edited items
                filtered_types.append(potential_type)

            elif not self.config.editorial[potential_type] and 'editors' not in item:
                # this type allows only non-edited items
                filtered_types.append(potential_type)

        self.logger.debug("Reduced types for {0} to {1}".format(item['title'], filtered_types))
        return filtered_types

    def _filter_by_peer_review(self, item, potential_types):
        """
        Reduces an item type list by its peer-review criteria
        :param item: the item
        :param potential_types: a list of potential types for the item
        :return: a list of filtered potential types
        """
        filtered_types = []

        for potential_type in potential_types:
            # determine whether the potential type matches the review criteria
            if self.config.peer_reviewed[potential_type] == 'ANY':
                # this type allows both peer-reviewed and non-peer-reviewed items
                filtered_types.append(potential_type)

            elif self.config.peer_reviewed[potential_type] and 'refereed' in item and item['refereed'] == 'TRUE':
                # this type allows only peer-reviewed items
                filtered_types.append(potential_type)

            elif not self.config.peer_reviewed[potential_type] and 'refereed' in item and item['refereed'] == 'FALSE':
                # this type allows only non-peer-reviewed items
                filtered_types.append(potential_type)

        self.logger.debug("Reduced types for {0} to {1}".format(item['title'], filtered_types))
        return filtered_types

    def _get_potential_types(self, item):
        """
        Builds a list of potential sub-types for an item, which can then be matched against for peer review criteria
        :param item: the JSON item from eprints
        :return: a list of potential sub-types for the item
        """
        sub_types = []

        for key, val in self.config.eprints_db.items():
            if val == item['type']:
                sub_types.append(key)

        self.logger.debug("Potential sub-types for item {0} are {1}".format(item['title'], sub_types))
        return sub_types

    def _parse_prechecks(self, check_types, load_json, types):
        """
        A set of pre-checks before we parse the JSON
        :param check_types: A shortcut to recheck types
        :param load_json: A shortcut to load the JSON
        :param types: A list of input types
        :return: True if checks OK, otherwise False
        """
        # if the user has asked us to load the JSON here as a shortcut, do it
        if load_json and not self._json_loaded:
            self.logger.debug("Loading JSON via shortcut")
            if not self._populate_json(self.refresh):
                return False

        # check if the JSON is loaded and error if not
        elif not self._json_loaded:
            self.logger.error("JSON is not loaded")
            return False

        # if the user has asked us to check the types here as a shortcut, do it
        if check_types and not self._type_safe:
            self.logger.debug("Checking types via shortcut")
            if not self._check_types(types):
                return False

        # make sure that we recognise all the types that are being passed in
        elif not self._type_safe:
            self.logger.error("Types are not safe")
            return False

        self.logger.debug("Prechecks all passed")
        return True

    def _check_types(self, types):
        """
        Checks that the correct configuration details exist for all types
        :param types: A list of types to check
        :return: True if types are OK, otherwise False
        """
        # make sure we have a storage entry, a peer review setting, and a heading for each type
        self.logger.debug("Checking that all types are valid")
        errors = []

        for input_type in types:
            if input_type not in self.config.storage:
                errors.append('No storage entry found for type {0}'.format(input_type))
            if input_type not in self.config.peer_reviewed:
                errors.append('No peer review setting found for type {0}'.format(input_type))
            if input_type not in self.config.editorial:
                errors.append('No editorial setting found for type {0}'.format(input_type))
            if input_type not in self.config.book_review:
                errors.append('No book review setting found for type {0}'.format(input_type))
            if input_type not in self.config.eprints_db:
                errors.append('No eprints_db setting found for type {0}'.format(input_type))

        if len(errors) > 0:
            for err in errors:
                self.logger.error(err)

            self._type_safe = False

            return False
        else:
            self._type_safe = True
            return True

    def fetch(self, types):
        """
        Fetches data from the repository and prepares the on-disk structure
        :param types: A list of types to parse from the repository
        :return: True if successful, otherwise False
        """
        # make sure that we recognise all the types that are being passed in
        if not self._check_types(types):
            return False

        # populate the JSON field
        if not self._populate_json(self.refresh):
            return False

        # attempt to parse the requested sections
        if not self._parse_json(types):
            return False
