import os
import re
import subprocess
from datetime import datetime


class TemplateBuilder:
    def __init__(self, repository, config, logger):
        self.repo = repository
        self.config = config
        self.logger = logger

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

        for item in section_items:
            creators, editors, the_date, volume, item = self._build_creators(item)

            if current_date != the_date:
                line = self._substitute_item_template(item_templates_new_date, the_date, creators, editors, volume, item)
                current_date = the_date
            else:
                line = self._substitute_item_template(item_templates, the_date, creators, editors, volume, item)

            output += line

        header_output = header_template.format(self.config.section_headings[section], len(section_items))

        section_output = section_template.format(section, header_output + output)

        return section_output

    def _substitute_item_template(self, template, the_date, creators, editors, volume, item):
        """
        Substitutes variables into an item template. There are five special tags: year, creators, editors,
        trailingcommacreators, and volume. The rest are drawn from the item dictionary.
        :param template: the template string
        :param the_date: the date to use
        :param creators: a creators string
        :param editors: an editors string
        :param volume: a volume string
        :param item: the eprints item
        :return: a formatted output line
        """
        # special fields
        line = template.replace('[[year]]', str(the_date))
        line = line.replace('[[creators]]', creators)
        line = line.replace('[[editors]]', editors)
        line = line.replace('[[volume]]', volume)
        line = line.replace('[[trailingcommacreators]]', ', ' if len(creators) > 0 else '')

        # all other fields drawn from item
        matches = re.findall(r'\[\[(.+?)\]\]', line)
        for match in matches:
            line = line.replace('[[{0}]]'.format(match), item[match])

        return line

    def _build_creators(self, item):
        """
        Builds a list of creators, editors, dates and titles for an item
        :param item: The item on which to work
        :return: a tuple of: creators (string), editors (string), dates, and titles
        """
        creators = ""
        editors = ""
        if 'creators' in item:
            for creator in item['creators'][:-1]:
                if creators != "":
                    creators += "; "

                creators += str.format('{0}, {1}', creator['name']['family'], creator['name']['given'])

            if creators != "":
                creators += "; and "

            creator = item['creators'][-1]

            creators += str.format('{0}, {1}', creator['name']['family'], creator['name']['given'])

        if 'editors' in item:
            for editor in item['editors'][:-1]:
                if editors == "" and creators == "":
                    editors = "; ed. by "
                elif editors == "":
                    editors = "; ed. by "
                if editors != "; ed. by " and editors != "; ed. by ":
                    editors += "; "

                editors += str.format('{0}, {1}', editor['name']['family'], editor['name']['given'])

            if editors == "" and creators == "":
                editors = "; ed. by "
            elif editors == "":
                editors = "; ed. by "
            if editors != "; ed. by " and editors != "; ed. by ":
                editors += "; "

            editor = item['editors'][-1]

            editors += str.format('{0}, {1}', editor['name']['family'], editor['name']['given'])

        try:
            the_date = datetime.strptime(item['date'][0:4], "%Y").year
        except:
            the_date = "n.d."

        if 'oa_status' in item and item['oa_status'] == 'gold' and 'official_url' in item:
            item['uri'] = item['official_url']

        # replace double quotation marks with singles
        item['title'] = item['title'].replace('"', '\'')
        item['title'] = item['title'].replace('“', '‘')
        item['title'] = item['title'].replace('”', '’')

        # build the volume/number format
        volume = ""

        if 'volume' in item and not 'number' in item:
            volume = ' ({0})'.format(str(item['volume']))
        elif 'number' in item and not 'volume' in item:
            volume = ' {0}'.format(str(item['number']))
        elif 'number' in item and 'volume' in item:
            volume = ' {0}({1})'.format(str(item['volume']), str(item['number']))

        return creators, editors, the_date, volume, item

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
            if match in self.config.section_headings:
                substitute = self._eprint_substitute(match, rule)
            else:
                try:
                    section_file = "sections/" + match
                    with open(section_file) as f:
                        content = [line.rstrip('\n') for line in f]
                        substitute = '\n'.join(content)
                except EnvironmentError:
                    self.logger.error('Cannot load section from {0}'.format(section_file))
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
