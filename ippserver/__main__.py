from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import logging
import sys

from . import behaviour
from .pc2paper import Pc2Paper
from .server import run_server, ThreadedTCPServer, ThreadedTCPRequestHandler


def parse_args():
	pdf_help = 'Request that CUPs sends the document as a PDF file, instead of a PS file. CUPs detects this setting when ADDING a printer: you may need to re-add the printer on a different port'

	parser = argparse.ArgumentParser(description='An IPP server')
	parser.add_argument('-v', '--verbose', action='count', help='Add debugging')
	parser.add_argument('-H', '--host', type=str, default='localhost', metavar='HOST', help='Address to listen on')
	parser.add_argument('-p', '--port', type=int, required=True, metavar='PORT', help='Port to listen on')

	parser_action = parser.add_subparsers(help='Actions', dest='action')

	parser_save = parser_action.add_parser('save', help='Write any print jobs to disk')
	parser_save.add_argument('--pdf', action='store_true', default=False, help=pdf_help)
	parser_save.add_argument('directory', metavar='DIRECTORY', help='Directory to save files into')

	parser_command = parser_action.add_parser('run', help='Run a command when recieving a print job')
	parser_command.add_argument('command', nargs=argparse.REMAINDER, metavar='COMMAND', help='Command to run')
	parser_command.add_argument('--pdf', action='store_true', default=False, help=pdf_help)

	parser_saverun = parser_action.add_parser('saveandrun', help='Write any print jobs to disk and the run a command on them')
	parser_saverun.add_argument('--pdf', action='store_true', default=False, help=pdf_help)
	parser_saverun.add_argument('directory', metavar='DIRECTORY', help='Directory to save files into')
	parser_saverun.add_argument('command', nargs=argparse.REMAINDER, metavar='COMMAND', help='Command to run (the filename will be added at the end)')

	parser_command = parser_action.add_parser('reject', help='Respond to all print jobs with job-canceled-at-device')

	parser_command = parser_action.add_parser('pc2paper', help='Post print jobs usign http://www.pc2paper.org/')
	parser_command.add_argument('--pdf', action='store_true', default=False, help=pdf_help)
	parser_command.add_argument('--config', metavar='CONFIG', help='File containging an address to send to, in json format')

	return parser.parse_args()

def behaviour_from_args(args):
	if args.action == 'save':
		return behaviour.SaveFilePrinter(
			directory=args.directory,
			filename_ext='pdf' if args.pdf else 'ps')
	if args.action == 'run':
		return behaviour.RunCommandPrinter(
			command=args.command,
			filename_ext='pdf' if args.pdf else 'ps')
	if args.action == 'saveandrun':
		return behaviour.SaveAndRunPrinter(
			command=args.command,
			directory=args.directory,
			filename_ext='pdf' if args.pdf else 'ps')
	if args.action == 'pc2paper':
		pc2paper_config = Pc2Paper.from_config_file(args.config)
		return behaviour.PostageServicePrinter(
			service_api=pc2paper_config,
			filename_ext='pdf' if args.pdf else 'ps')
	if args.action == 'reject':
		return behaviour.RejectAllPrinter()
	raise RuntimeError(args)

def main(args):
	logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

	server = ThreadedTCPServer(
		(args.host, args.port),
		ThreadedTCPRequestHandler,
		behaviour_from_args(args))
	run_server(server)

if __name__ == "__main__":
	main(parse_args())
