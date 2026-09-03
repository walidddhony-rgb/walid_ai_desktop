try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


class SearchEngine:
    @staticmethod
    def web_search(query, limit=6):
        if not DDGS:
            return []
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=limit):
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        }
                    )
        except Exception:
            return []
        return results

    @staticmethod
    def academic_search(query, limit=6):
        if not DDGS:
            return []
        scoped = f"{query} site:pubmed.ncbi.nlm.nih.gov OR site:doi.org OR site:semanticscholar.org"
        candidates = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(scoped, max_results=limit * 2):
                    url = r.get("href", "")
                    score = 0
                    if "pubmed" in url:
                        score += 3
                    if "doi.org" in url:
                        score += 2
                    if "semanticscholar" in url:
                        score += 2
                    candidates.append(
                        {
                            "title": r.get("title", ""),
                            "url": url,
                            "snippet": r.get("body", ""),
                            "score": score,
                        }
                    )
        except Exception:
            return []
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return [{k: v for k, v in c.items() if k != "score"} for c in candidates[:limit]]
