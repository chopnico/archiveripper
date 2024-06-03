# ripper.py
# Copyright (c) 2020  James Shiffer
# This file contains the main application logic.

import argparse, api, getpass, logging, os, sys
from tqdm import trange
from config import config

def main():
    completed = False
    logging.basicConfig(level=logging.INFO)

    # Parse book id and credentials
    parser = argparse.ArgumentParser()
    parser.add_argument('id', nargs='?',
        help='Look for the book\'s identifier (the part of the url immediately after "https://archive.org/details/").')
    parser.add_argument('-u', '--username', help='Your archive.org account\'s email.')
    parser.add_argument('-p', '--password', help='Your archive.org account\'s password')
    parser.add_argument('-a', '--all-pages', action='store_true', help='Download every page of the book')
    parser.add_argument('-s', '--page-start', type=int, help='Download pages starting at page number N and ending at the book\'s last page, or a range if --page-end has been specified')
    parser.add_argument('-e', '--page-end', type=int, help='End of the range of page numbers to download')
    parser.add_argument('-d', '--output-dir', help='Directory you want the pages to be written to. If undefined the directory will be named the book id')
    parser.add_argument('-S', '--scale', default=0, type=int, help='Image resolution of the pages requested, can save bandwidth if the best image quality isn\'t necessary. Higher integers mean smaller resolution, default is 0 (no downscaling)')
    parser.add_argument('-q', '--quiet', default=False, action=argparse.BooleanOptionalAction, help="Does not ask for confirmation to continue if folder is found.")
    args = parser.parse_args()

    id = args.id
    username = args.username
    password = args.password

    #If any of the credentials isn't specified with cmdline args ask for it interactively
    if not args.id:
        print('Look for the book\'s identifier (the part of the url immediately after "https://archive.org/details/").')
        id = input('Enter it here: ')
        logging.debug('received book ID: %s' % id)
    if not username:
        # Check if the email and password of user are stored in config file
        if config['email']:
            username = config['email']
        else:
            username = input('Enter your archive.org email: ')
    if not password:
        # Check if the email and password of user are stored in config file
        if config['password']:
            password = config['password']
        else:
            password = input('Enter your archive.org password: ')


    if not args.output_dir:
        dir = './output/' + id
    else:
        dir = os.path.expanduser(args.output_dir)

    logging.debug('creating output dir "%s"' % dir)
    if not args.quiet:
        if os.path.isdir(dir):
            response = input('Output folder %s already exists. Continue? ' \
                             % dir)
            if not response.lower().startswith('y'):
                return
        else:
            os.mkdir(dir)

    start = 0
    for i in range(3):
        restart = False
        print(f"Attempt {i + 1}")
        client = api.ArchiveReaderClient()

        logging.debug('attempting login with user-supplied credentials')
        client.login(username, password)

        logging.debug('attempting to start scheduler')
        client.schedule_loan_book(id)

        page_count = client.fetch_book_metadata()

        end = page_count

        if not args.all_pages:
            if not args.page_start and not args.page_end:
                print('The book is %d pages long. Which pages do you want?' % page_count)
                desired_pages = input('Enter a range (eg. 1-15) or leave blank for all: ')

                if desired_pages:
                    [start, end] = desired_pages.split('-')
                    start = int(start) - 1
                    end = int(end)
            else:
                if args.page_start: start = args.page_start - 1
                if args.page_end: end = args.page_end

        logging.debug('planning on fetching pages %d thru %d' % (start, end))

        for i in trange(start, end):
            contents = client.download_page(i, args.scale)
            if contents is not None:
                with open('%s/%04d.jpg' % (dir, i + 1), 'wb') as file:
                    file.write(contents)
            else:
                restart = True
                start = i + 1
                args.all_pages = False
                args.quiet = True
                break

        if not restart:
            client.return_book(id)
            print ('book returned')
            completed = True
            break

    if completed:
        print('finished downloading book')
    else:
        print('book did not finish downloading')

if __name__ == '__main__':
    main()
