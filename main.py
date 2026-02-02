import sys
import click
from yaspin import yaspin
from datetime import datetime
from scrape import scrape_multiple
from search import get_search_results
from llm import get_llm, refine_query, filter_results, generate_summary
from llm_utils import get_model_choices

MODEL_CHOICES = get_model_choices()

@click.group()
@click.version_option()
def darkk():
    """Darkk: AI-Powered Dark Web OSINT Tool."""
    pass

@darkk.command()
@click.option(
    "--model", "-m",
    default="gpt-5-mini",
    show_default=True,
    type=click.Choice(MODEL_CHOICES),
    help="Select LLM model to use (e.g., ChatGPT models, Claude models, Gemini models, Ollama models, Openrouter models)",
)
@click.option("--query", "-q", required=True, type=str, help="Dark web search query")
@click.option("--threads", "-t", default=5, show_default=True, type=int, help="Number of threads (Default: 5)")
@click.option("--output", "-o", type=str, help="Filename to save the final summary.")
def cli(model, query, threads, output):
    """Run Darkk in CLI mode."""
    try:
        llm = get_llm(model)

        # Show spinner while processing
        with yaspin(text="Processing...", color="cyan") as sp:
            sp.write(f"🔹 Initializing with model: {model}")

            refined_query = refine_query(llm, query)
            sp.write(f"🔹 Refined Query: {refined_query}")

            search_results = get_search_results(refined_query, max_workers=threads)
            if not search_results:
                sp.fail("✖")
                click.echo("\n[ERROR] No search results found. Tor may be unstable or query returned 0 hits.")
                return

            sp.write(f"🔹 Found {len(search_results)} raw results. Filtering...")
            search_filtered = filter_results(llm, refined_query, search_results)

            sp.write(f"🔹 Scraping {len(search_filtered)} relevant sites...")
            scraped_results = scrape_multiple(search_filtered, max_workers=threads)

            if not scraped_results:
                sp.fail("✖")
                click.echo("\n[ERROR] Failed to scrape any content. Check Tor connection.")
                return

            sp.ok("✔")

        # Generate summary
        click.echo("\n🔹 Generating Intelligence Summary...")
        summary = generate_summary(llm, query, scraped_results)

        # Save output
        if not output:
            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"summary_{now}.md"
        else:
            filename = output + ".md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(summary)
            click.echo(f"\n[OUTPUT] Final intelligence summary saved to {filename}")

    except KeyboardInterrupt:
        click.echo("\n\n[!] Operation cancelled by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)


@darkk.command()
@click.option("--ui-port", default=8501, show_default=True, type=int, help="Port for Streamlit UI")
@click.option("--ui-host", default="localhost", show_default=True, type=str, help="Host for Streamlit UI")
def ui(ui_port, ui_host):
    """Run Darkk in Web UI mode."""
    import sys, os
    from streamlit.web import cli as stcli

    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(__file__)

    ui_script = os.path.join(base, "ui.py")
    sys.argv = [
        "streamlit", "run", ui_script,
        f"--server.port={ui_port}",
        f"--server.address={ui_host}",
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    darkk()
