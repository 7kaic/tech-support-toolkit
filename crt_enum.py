"""
Enumera subdomínios via crt.name e testa quais respondem por HTTP/HTTPS.
Uso: python crt_enum.py dominio.com
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://crt.name/v1/search"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ReconBot/1.0)"}
TIMEOUT = 8
WORKERS = 30

class Host(NamedTuple):
    name: str
    scheme: str
    status: int
    server: str

def buscar_subdominios(apex: str) -> list[str]:
    r = requests.get(API_URL, params={"apex": apex}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    nomes = {linha.strip().lower().removeprefix("*.") for linha in r.text.splitlines()}
    return sorted(n for n in nomes if n == apex or n.endswith(f".{apex}"))

def probe(host: str) -> Host | dict:
    """Tenta HTTPS e depois HTTP; devolve None se nenhum responder."""
    for scheme in ("https", "http"):
        try:
            r = requests.get(
                f"{scheme}://{host}/", headers=HEADERS, timeout=TIMEOUT, verify=False
            )
        except requests.RequestException:
            continue
        return Host(host, scheme, r.status_code, r.headers.get("Server", "-"))
    return None

def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python crt_enum.py dominio.com")

    apex = sys.argv[1].lower().strip().rstrip(".")

    print(f"[*] Enumerando {apex}...", file=sys.stderr)
    subs = buscar_subdominios(apex)
    print(f"[+] {len(subs)} subdomínios encontrados:\n")
    print("\n".join(subs))

    if not subs or input("\nTestar HTTP/HTTPS nesses hosts? [S/n] ").strip().lower() in ("n", "nao", "não"):
        return

    print(f"Testando com {WORKERS} threads...", file=sys.stderr)
    with ThreadPoolExecutor(WORKERS) as pool:
        vivos = sorted(filter(None, pool.map(probe, subs)))

    print(f"[+] Vivos: {len(vivos)} / {len(subs)}\n")
    for h in vivos:
        print(f"{h.status:>3}  {h.scheme:<5}  {h.name:<50}  {h.server}")
 
if __name__ == "__main__":
    main()