import os
import re
import subprocess
from datetime import datetime


class TemplateBuilder:
    def __init__(self, repository, config, logger):
        self.repo = repository
        self.config = config
        self.logger = logger

        self.cached_italic_regexen = []

    def build(self, rules):
        """
        Run an output ruleset
        :param rules: the rules to run
        :return: True if successful, False otherwise
        """
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
        item_templates = self.config.item_templates[rule][section]
        item_templates_new_date = self.config.item_templates_new_date[rule][section]

        # get the items from the repo
        self.logger.debug("Fetching {0} from repo".format(section))
        section_items = self.repo.__getattr__(section)

        current_date = ''

        output = ''

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
                # build the template components
                creators = self._build_creators(item, rule)
                editors = self._build_editors(item, creators, rule)
                the_date = self._build_date(item)
                volume = self._build_volume(item, rule)
                oa_status = self._build_oa_status(item, rule)

                # replace title quotes
                self._replace_title_quotes(item)

                # replace URLs
                self._link_to_official_url_if_gold_oa(item, rule)

                # italicize title
                self._italicize_titles(item, rule)

                if current_date != the_date:
                    line = self._substitute_item_template(item_templates_new_date, the_date, creators, editors, volume,
                                                          oa_status, item)
                    current_date = the_date
                else:
                    line = self._substitute_item_template(item_templates, the_date, creators, editors, volume,
                                                          oa_status, item)

                output += line

        if item_count > 0:
            header_output = header_template.format(self.config.section_headings[rule][section], item_count)

            section_output = section_template.format(section, header_output + output)
        else:
            section_output = ''

        return section_output

    def _substitute_item_template(self, template, the_date, creators, editors, volume, oa_status, item):
        """
        Substitutes variables into an item template. There are six special tags: year, creators, editors,
        trailingcommacreators, oa_status, and volume. The rest are drawn from the item dictionary.
        :param template: the template string
        :param the_date: the date to use
        :param creators: a creators string
        :param editors: an editors string
        :param volume: a volume string
        :param oa_status: a string with an OA link
        :param item: the eprints item
        :return: a formatted output line
        """
        # special fields
        line = template.replace('[[year]]', str(the_date))
        line = line.replace('[[creators]]', creators)
        line = line.replace('[[editors]]', editors)
        line = line.replace('[[oa_status]]', oa_status)
        line = line.replace('[[volume]]', volume)
        line = line.replace('[[trailingcommacreators]]', ', ' if len(creators) > 0 else '')

        # all other fields drawn from item
        matches = re.findall(r'\[\[(.+?)\]\]', line)
        for match in matches:
            line = line.replace('[[{0}]]'.format(match), item[match])

        return line

    def _person_formatter(self, creator, is_primary, rule, field_top_level, given_name_field, last_name_field,
                          primary_surname_first_field, other_surname_first_field):
        """
        Formats a creator line
        :param creator: the creator object
        :param is_primary: whether this is the first creator in the list
        :param rule: the current rule
        :return: a formatted creator string
        """
        if is_primary:
            # this is a primary person
            if primary_surname_first_field[rule]:
                # render the surname first
                return str.format('{0}, {1}',
                                  creator[field_top_level][last_name_field],
                                  creator[field_top_level][given_name_field])
            else:
                # render as a full name
                return str.format('{1} {0}',
                                  creator[field_top_level][last_name_field],
                                  creator[field_top_level][given_name_field])

        else:
            # this is a secondary person
            if other_surname_first_field[rule]:
                # render the surname first
                return str.format('{0}, {1}',
                                  creator[field_top_level][last_name_field],
                                  creator[field_top_level][given_name_field])
            else:
                # render as a full name
                return str.format('{1} {0}',
                                  creator[field_top_level][last_name_field],
                                  creator[field_top_level][given_name_field])

    def _build_editors(self, item, creators, rule):
        """
        Builds a list of editors for an item
        :param item: The item on which to work
        :param creators: The current string of creators
        :param rule: The current rule
        :return: a string of editors
        """
        editors = ""
        is_primary = True

        if self.config.editors_item_name in item:
            for editor in item[self.config.editors_item_name][:-1]:
                if editors == "" and creators == "":
                    editors = self.config.editors_prefix[rule]
                elif editors == "":
                    editors = self.config.editors_prefix[rule]
                if editors != self.config.editors_prefix[rule]:
                    is_primary = False
                    editors += self.config.editors_delimiter[rule]

                editors += self._person_formatter(editor, is_primary, rule, self.config.creator_field_top_level,
                                                  self.config.editor_field_given_name,
                                                  self.config.editor_field_last_name,
                                                  self.config.primary_editor_surname_first,
                                                  self.config.other_editors_surname_first)

            if editors == "" and creators == "":
                editors = self.config.editors_prefix[rule]
            elif editors == "":
                editors = self.config.editors_prefix[rule]
            if editors != self.config.editors_prefix[rule]:
                is_primary = False
                if len(item[self.config.editors_item_name]) > 2:
                    editors += self.config.editors_terminal_delimiter[rule]
                else:
                    editors += self.config.editors_terminal_delimiter_two[rule]

            editors += self._person_formatter(item[self.config.editors_item_name][-1], is_primary, rule,
                                              self.config.creator_field_top_level,
                                              self.config.editor_field_given_name,
                                              self.config.editor_field_last_name,
                                              self.config.primary_editor_surname_first,
                                              self.config.other_editors_surname_first)

        return editors

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

    def _build_date(self, item):
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

    def _replace_title_quotes(self, item):
        if self.config.outer_quotes_single:
            # do nothing as it's hard to detect possessive apostrophes
            pass
        else:
            # replace double quotation marks with singles
            item['title'] = item['title'].replace('"', '\'')
            item['title'] = item['title'].replace('“', '‘')
            item['title'] = item['title'].replace('”', '’')

    def _build_volume(self, item, rule):
        """
        Builds a volume and issue string
        :param item: The item on which to work
        :param rule: The rule on which to operate
        :return: a tuple of: creators (string), editors (string), dates, and titles
        """
        # build the volume/number format
        volume = self.config.volume_template[rule]

        if 'volume' in item:
            volume = volume.replace('[[volume]]', str(item['volume']))
        else:
            volume = volume.replace('[[volume]]', '')

        if 'number' in item:
            if self.config.number_in_brackets:
                volume = volume.replace('[[number]]', '({0})'.format(str(item['number'])))
            else:
                volume = volume.replace('[[number]]', str(item['number']))
        else:
            volume = volume.replace('[[number]]', '')

        return volume

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

    def _build_creators(self, item, rule):
        """
        Builds a list of creators, editors, dates and titles for an item
        :param item: The item on which to work
        :param rule: The rule on which to operate
        :return: a string of creators
        """
        creators = ""
        is_primary = True

        if self.config.creators_item_name in item:
            for creator in item[self.config.creators_item_name][:-1]:
                if creators != "":
                    creators += self.config.creators_delimiter[rule]
                    is_primary = False

                creators += self._person_formatter(creator, is_primary, rule,
                                                   self.config.creator_field_top_level,
                                                   self.config.creator_field_given_name,
                                                   self.config.creator_field_last_name,
                                                   self.config.primary_creator_surname_first,
                                                   self.config.other_creators_surname_first)

            if creators != "":
                if len(item[self.config.creators_item_name]) > 2:
                    creators += self.config.creators_terminal_delimiter[rule]
                else:
                    creators += self.config.creators_terminal_delimiter_two[rule]
                is_primary = False

            creators += self._person_formatter(item[self.config.creators_item_name][-1], is_primary, rule,
                                               self.config.creator_field_top_level,
                                               self.config.creator_field_given_name,
                                               self.config.creator_field_last_name,
                                               self.config.primary_creator_surname_first,
                                               self.config.other_creators_surname_first)

        return creators

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
