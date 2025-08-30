# WikiToPDF

Traversing video game wikis is very time consuming and can accidetally lead to spoilers being uncovered. By switching to using a language model you can ask specific questions and quickly get information about the game.  You do lose all visual information but the new flexibility of information makes up for it. I've also found it helpful for understanding basic game play mechanics I might have missed out on discovering.

WikiToPDF is a Python script that downloads an entire MediaWiki-based wiki and converts it into a series of PDF files. It is designed to be a powerful tool for creating an interactive version of any game wiki.

## Features

- **Full Wiki Scraping**: The script can crawl an entire wiki, starting from the `Special:AllPages` page and following all "Next page" links to ensure every page is captured.
- **Local Caching**: To save time and bandwidth on subsequent runs, the script caches the text content of each wiki page in a local folder. It will only download a page if it's not already in the cache.
- **Robust Error Handling**: The script is designed to handle interruptions. If a download is stopped prematurely, it will re-download the last page on the next run to ensure the cache is not corrupted.
- **PDF Generation**: The script converts the cached text files into a series of PDF files, with each wiki page as a separate chapter.
- **Batch Processing**: To avoid creating a single, massive PDF file, the script splits the output into multiple PDFs, with each PDF containing 100 pages.
- **Organized Output**: The script creates a main `all_wiki` directory. Inside this directory, it creates a folder for the cached text files (e.g., `terraria_fandom_com_txt`) and a separate folder for the generated PDFs (e.g., `terraria_fandom_com_wiki_PDF`), keeping your project directory clean and organized.

## Known Bugs

Sometimes the page doesn't download. Still unsure why this happening since so many other pages download just fine.

## Usage

To use the script, run it from the command line with the URL of any page on the target wiki:

```bash
python download.py <url_to_any_wiki_page>
```

For example:

```bash
python download.py https://terraria.fandom.com/wiki/Terraria_Wiki
```

The script will automatically determine the base URL of the wiki and start the process.

## Purpose: Interactive Wiki with NotebookLM

The primary purpose of this script is to generate a set of PDF files that can be uploaded to [NotebookLM](https://notebooklm.google.com/). By using the generated PDFs as a source, you can create a powerful, interactive, and conversational AI model of any game wiki.

This allows you to:

-   Ask questions about the game in natural language.
-   Get instant summaries of complex topics.
-   Create a personalized and interactive guide to your favorite games.

Simply run the script, wait for the PDFs to be generated, and then upload them to NotebookLM to start exploring your favorite game wikis in a whole new way.
