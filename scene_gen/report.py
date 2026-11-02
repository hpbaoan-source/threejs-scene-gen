"""Human-readable run summary."""

WIDTH = 78


def _rule(char="-"):
    return char * WIDTH


def summary(result, log=print):
    log("")
    log(_rule("="))
    log(f"PROMPT: {result.prompt}")
    log(_rule("="))
    for attempt in result.attempts:
        review = attempt.review or {}
        log(f"attempt {attempt.index}  ({attempt.seconds:.1f}s)")
        if attempt.static_problems:
            log("  static : " + "; ".join(attempt.static_problems))
        if attempt.render_report:
            image = attempt.render_report.get("image") or {}
            log(
                "  render : %d loi console | meanLuma=%s stdLuma=%s dark=%s"
                % (
                    attempt.render_report.get("consoleErrorCount", 0),
                    image.get("meanLuma"),
                    image.get("stdLuma"),
                    image.get("darkRatio"),
                )
            )
        if review:
            log(
                "  review : %s (score %s) %s"
                % (review.get("verdict"), review.get("score"), review.get("scores") or "")
            )
            for issue in review.get("issues") or []:
                log("     - " + issue)
            for fix in review.get("fixes") or []:
                log("     > " + fix)
        log("  verdict: " + (attempt.reason or "-"))
        log("")
    log(_rule())
    log(f"final    : {result.best.html_path if result.best else '-'}")
    log(f"render   : {result.best.png_path if result.best else '-'}")
    log(f"stop     : {result.stop_reason}")
    log(f"time     : {result.total_seconds:.1f}s")
    log(f"cost     : ${result.total_cost:.5f}")
    log(_rule())
