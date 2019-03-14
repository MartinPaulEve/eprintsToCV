# this specifies the base eprints URL and the user page
eprints = {
    'repo': 'eprints.bbk.ac.uk',
    'user': 'Eve=3AMartin_Paul=3A=3A'}

# this controls the output headings in the template
section_headings = {'all_books': "BOOKS",
                    'unedited_books': "BOOKS",
                    'edited_books': "EDITED VOLUMES",
                    'all_peer_reviewed_articles': "PEER-REVIEWED ARTICLES",
                    'peer_reviewed_articles': "PEER-REVIEWED ARTICLES",
                    'other_articles': "OTHER ARTICLES / MEDIA / INTERVIEWS",
                    'reviews': "REVIEWS",
                    'book_chapters': "BOOK CHAPTERS",
                    'conference_items': "CONFERENCE PAPERS/EVENTS"}

# this determines the peer review conditions for each input type
peer_reviewed = {'all_books': "ANY",
                 'unedited_books': True,
                 'edited_books': True,
                 'all_peer_reviewed_articles': True,
                 'peer_reviewed_articles': True,
                 'other_articles': False,
                 'reviews': "ANY",
                 'book_chapters': True,
                 'conference_items': "ANY"}

# this determines the editorial conditions for each input type
editorial = {'all_books': "ANY",
             'unedited_books': False,
             'edited_books': True,
             'all_peer_reviewed_articles': "ANY",
             'peer_reviewed_articles': "ANY",
             'other_articles': "ANY",
             'reviews': "ANY",
             'book_chapters': "ANY",
             'conference_items': "ANY"}

# this determines the book review conditions for each input type (if the text starts with "Review of"
book_review = {'all_books': False,
               'unedited_books': False,
               'edited_books': False,
               'all_peer_reviewed_articles': False,
               'peer_reviewed_articles': False,
               'other_articles': False,
               'reviews': True,
               'book_chapters': False,
               'conference_items': False}

# this determines the underlying database type in eprints
eprints_db = {'all_books': "book",
              'unedited_books': "book",
              'edited_books': "book",
              'all_peer_reviewed_articles': "article",
              'peer_reviewed_articles': "article",
              'other_articles': "article",
              'reviews': "article",
              'book_chapters': "book_section",
              'conference_items': "conference_item"}

# this section determines data storage locations
storage = {'json': 'data/eprints.json',
           'all_books': "data/all_books.json",
           'unedited_books': "data/unedited_books.json",
           'edited_books': "data/edited_books.json",
           'all_peer_reviewed_articles': "data/all_peer_reviewed_articles.json",
           'peer_reviewed_articles': "data/peer_reviewed_articles.json",
           'other_articles': "data/other_articles.json",
           'reviews': "data/reviews.json",
           'book_chapters': "data/book_sections.json",
           'conference_items': "data/conference_items.json"
           }

# this controls the default types to parse if nothing is given on the command line
default_types = ['unedited_books', 'edited_books', 'peer_reviewed_articles']
