import os
import re
import subprocess
from datetime import datetime

import requests


class CiteProc:
    def __init__(self, repo, config, logger):
        self.config = config
        self.logger = logger
        self.repo = repo

        self.cached_italic_regexen = []

        # start the citeproc server
        self.init_commands = ['screen -S serve_npm -d -m bash -c "npm start"',
                              'sleep 2']

        for shell_script in self.init_commands:
            subprocess.call(shell_script, shell=True, cwd=self.config.citeproc_js_server_directory)

        self.logger.info('Started citeproc-js-server')

    def shutdown(self):
        """
        Shutdown the NPM citeproc-js server
        :return: Nothing
        """

        shutdown_commands = ['screen -S serve_npm -X quit']

        for shell_script in shutdown_commands:
            subprocess.call(shell_script, shell=True)

        self.logger.info('Shutdown citeproc-js-server')

    def build(self, rules):
        for rule in rules:
            # load the ruleset
            if rule not in self.config.output_rules:
                self.logger.error("Ruleset {0} is not defined".format(rule))
                return False

            self.logger.debug("Loading ruleset for {0}".format(rule))
            ruleset = self.config.output_rules[rule]

            template_file = ruleset[0]
            output_file = ruleset[1]

            template = self._load_template(template_file)

            if not template:
                return False

            template = self._substitute_template(template, rule)

            if not template:
                return False

            try:
                # write the output to the output file
                with open(output_file, "w") as out_file:
                    out_file.write(template)
            except EnvironmentError:
                self.logger.error('Cannot write output to {0}'.format(output_file))
                # try to delete the file
                os.remove(output_file)
                return False

            # run any remaining shell scripts
            if len(ruleset) > 2:
                counter = 0
                for shell_script in ruleset:
                    if counter < 2:
                        counter += 1
                    else:
                        self.logger.debug("Calling shell script {0}".format(shell_script))
                        subprocess.call(shell_script, shell=True)
        return True

    def _load_template(self, template):
        """
        Load a template file from disk
        :param template: the file to load
        :return: a string of the template or None if the operation fails
        """
        try:
            with open(template, 'r') as f:
                content = [line.rstrip('\n') for line in f]

            return '\n'.join(content)
        except EnvironmentError:
            self.logger.error('Cannot load template from {0}'.format(template))
            return None

    def _substitute_template(self, template, rule):
        """
        Substitute in sections and eprint sections into a template document
        :param template: the template string
        :return: a substituted template
        """
        matches = re.findall('{{(.+?)}}', template)
        for match in matches:
            self.logger.debug("Processing template section '{0}'".format(match))
            section = re.compile(r'{{' + match + '}}')
            if match in self.config.section_headings[rule]:
                substitute = self._eprint_substitute(match, rule)
            else:
                try:
                    section_file = "sections/" + match
                    with open(section_file) as f:
                        content = [line.rstrip('\n') for line in f]
                        substitute = '\n'.join(content)
                except EnvironmentError:
                    self.logger.error('Cannot load section.')
                    return False

            template = section.sub(substitute, template)

        return template

    @staticmethod
    def _build_date(item):
        """
        Builds a date for an item
        :param item: The item on which to work
        :return: a formatted date
        """
        try:
            the_date = datetime.strptime(item['date'][0:4], "%Y").year
        except:
            the_date = "n.d."

        return the_date

    def _italicize_titles(self, item, rule):
        """
        Italicizes titles
        :param item: The item on which to work
        :param rule: The current rule
        :return: nothing
        """
        if not self.config.italicize_titles[rule]:
            return

        # build a cached list of italic regexen if it doesn't exist
        if len(self.cached_italic_regexen) == 0:
            for italic in self.config.titles_to_italicize:
                self.cached_italic_regexen.append(re.compile(r'(\W|^)({0})(\W|$)'.format(italic)))

        for italic in self.cached_italic_regexen:
            item['title'] = re.sub(italic, r'\1<i>\2</i>\3', item['title'])

    def _link_to_official_url_if_gold_oa(self, item, rule):
        """
        If setting is enabled, change the link to the official URL if it's open access
        :param item: The item on which to work
        :param rule: The rule on which to operate
        :return: nothing
        """
        if self.config.gold_oa_direct_link[rule]:
            if 'oa_status' in item and item['oa_status'] == 'gold' and 'official_url' in item:
                item['uri'] = item['official_url']

    def _build_oa_status(self, item, rule):
        """
        Builds an open access status for an item
        :param item: The item on which to work
        :param rule: The rule on which to operate
        :return: a string of the OA status of the item
        """
        oa_status = ""

        if rule in self.config.oa_status:
            oa_status = self.config.oa_status[rule]
            non_oa_status = self.config.non_oa_status[rule]

            if 'oa_status' in item:
                if item['oa_status'] == 'green' or item['oa_status'] == 'gold':
                    oa_color = 'goldenrod' if item['oa_status'] == 'gold' else item['oa_status']
                    if 'files' in item:
                        oa_status = oa_status.replace('[[oa_uri]]',
                                                      item["files"][0]["url"]).replace('[[oa_color]]',
                                                                                       oa_color).replace('[[doc]]',
                                                                                                         '')
                    elif 'documents' in item:
                        if len(item['documents']) > 1:
                            for doc in item['documents']:
                                if 'formatdesc' in doc:
                                    oa_status = oa_status.replace('[[oa_uri]]',
                                                                  doc["uri"]).replace('[[oa_color]]',
                                                                                      oa_color).replace(
                                        '[[doc]]', ' {0}'.format(doc["formatdesc"]))
                                else:
                                    oa_status = oa_status.replace('[[oa_uri]]',
                                                                  doc["uri"]).replace('[[oa_color]]',
                                                                                      oa_color).replace(
                                        '[[doc]]', '')
                        else:
                            oa_status = oa_status.replace('[[oa_uri]]',
                                                          item["documents"][0]["uri"]).replace('[[oa_color]]',
                                                                                               oa_color).replace(
                                '[[doc]]', '')
                    else:
                        oa_status = non_oa_status.replace('[[email]]', self.config.email).replace('[[title]]',
                                                                                                  item['title'])
            else:
                oa_status = non_oa_status.replace('[[email]]', self.config.email).replace('[[title]]', item['title'])

        return oa_status

    @staticmethod
    def _substitute_item_template(template, citeproc, the_date, item, oa_status):
        """
        Substitutes variables into an item template. This handles [[year]], [[oa_status]] and [[citeproc]].
        :param template: the template string
        :param the_date: the date to use
        :param item: the eprints item
        :return: a formatted output line
        """

        # horrible hack
        citeproc = citeproc.replace('<div', '<a href="{0}"'.format(item['uri']))
        citeproc = citeproc.replace('</div', '</a')

        # special fields
        line = template.replace('[[citeproc]]', citeproc)
        line = line.replace('[[year]]', str(the_date))
        line = line.replace('[[oa_status]]', oa_status)

        return line

    def _eprint_substitute(self, section, rule):
        """
        Substitute in a section from the repository
        :param section: the section
        :param rule: the rule
        :return: the output for a section
        """
        # load up the templates for this section
        self.logger.debug("Loading sub-templates for {0} {1}".format(rule, section))
        section_template = self.config.section_template[rule]
        header_template = self.config.header_template[rule]
        item_templates = self.config.citeproc_item_templates[rule][section]
        item_templates_new_date = self.config.citeproc_item_templates_new_date[rule][section]

        # get the items from the repo
        self.logger.debug("Fetching {0} from repo".format(section))
        section_items = self.repo.__getattr__(section)

        current_date = ''

        output = {}
        items = {}
        counter = 0
        ordering = []

        output['items'] = items
        output_string = ''

        exclude_items = self.config.exclude_venues

        item_count = len(section_items)

        if rule in exclude_items and section in exclude_items[rule]:
            exclude_venues = exclude_items[rule][section].split(',')
        else:
            exclude_venues = []

        for item in section_items:
            if 'publication' in item and item['publication'] in exclude_venues:
                item_count -= 1
            else:
                # format the date
                the_date = self._build_date(item)

                # italicize title
                self._italicize_titles(item, rule)

                # setup official links for gold OA
                self._link_to_official_url_if_gold_oa(item, rule)

                # build the oa_status
                oa_status = self._build_oa_status(item, rule)

                # build the JSON
                identifier = '{0}-{1}'.format(counter, the_date)
                items[identifier] = {}
                ordering.append(items[identifier])

                items[identifier]['id'] = identifier
                items[identifier]['title'] = item['title']

                # build the authors list
                if self.config.creators_item_name in item and len(item[self.config.creators_item_name]) > 0:
                    items[identifier]['author'] = []

                    for creator in item[self.config.creators_item_name]:
                        creator_dict = {
                            'family': creator[self.config.creator_field_top_level][self.config.creator_field_last_name],
                            'given': creator[self.config.creator_field_top_level][self.config.creator_field_given_name]}

                        items[identifier]['author'].append(creator_dict)

                # build the editors list
                if self.config.editors_item_name in item and len(item[self.config.editors_item_name]) > 0:
                    items[identifier]['editor'] = []

                    for editor in item[self.config.editors_item_name]:
                        editor_dict = {
                            'family': editor[self.config.editor_field_top_level][self.config.editor_field_last_name],
                            'given': editor[self.config.editor_field_top_level][self.config.editor_field_given_name]}

                        items[identifier]['editor'].append(editor_dict)

                # the item type
                items[identifier]['type'] = self.config.citeproc_type_mapper[section]

                # publisher
                if 'publisher' in item:
                    items[identifier]['publisher'] = item['publisher']

                # place of publication
                if 'place_of_pub' in item:
                    items[identifier]['publisher-place'] = item['place_of_pub']

                # date
                items[identifier]['issued'] = {'date-parts': [[the_date]]}

                # container
                if 'publication' in item:
                    items[identifier]['container-title'] = item['publication']

                # volume and issue
                if 'volume' in item:
                    items[identifier]['volume'] = item['volume']

                if 'number' in item:
                    try:
                        items[identifier]['issue'] = int(item['number'])
                    except ValueError:
                        items[identifier]['issue'] = item['number']

                # doi
                if 'doi' in item:
                    items[identifier]['DOI'] = item['doi']

                # conference stuff
                if 'event_title' in item:
                    items[identifier]['event'] = item['event_title']
                    items[identifier]['container-title'] = item['event_title']

                if 'event_location' in item:
                    items[identifier]['event-place'] = item['event_location']

                # we have to do this _every_ time sadly because otherwise the CSL substitutes in "---"
                r = requests.post(
                    '{0}?bibliography=1&responseformat=json&style={1}'.format(self.config.citeproc_server,
                                                                              self.config.citeproc_style[rule]),
                    json=output)

                json_response = r.json()

                if len(json_response['bibliography'][1]) > 0:
                    if current_date != the_date:
                        line = self._substitute_item_template(item_templates_new_date,
                                                              json_response['bibliography'][1][0], the_date,
                                                              item, oa_status)
                        current_date = the_date
                    else:
                        line = self._substitute_item_template(item_templates,
                                                              json_response['bibliography'][1][0], the_date,
                                                              item, oa_status)

                    output_string += line

                output = {}
                items = {}
                output['items'] = items

                counter += 1

        if item_count > 0:
            header_output = header_template.format(self.config.section_headings[rule][section], item_count)

            section_output = section_template.format(section, header_output + output_string)
        else:
            section_output = ''

        return section_output
