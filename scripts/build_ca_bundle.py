"""Write .certs/ca-bundle.pem = certifi's bundle + the Windows trust store. Windows only.

Needed when antivirus HTTPS scanning (e.g. Avast Web Shield) re-signs
certificates with a root that Windows trusts but curl_cffi does not. Run once,
then add to .env:
    CA_BUNDLE=.certs/ca-bundle.pem
This does not turn off verification: certificates are still checked, against the
same roots Windows already trusts.
"""
import ssl
import sys
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parents[1]

if sys.platform != "win32":
    sys.exit("Only needed on Windows; leave CA_BUNDLE unset elsewhere.")

windows_pems = [ssl.DER_cert_to_PEM_cert(cert)
                for store in ("ROOT", "CA")
                for cert, encoding, _trust in ssl.enum_certificates(store)
                if encoding == "x509_asn"]

out = ROOT / ".certs" / "ca-bundle.pem"
out.parent.mkdir(exist_ok=True)
out.write_text(Path(certifi.where()).read_text(encoding="utf-8") + "\n" + "\n".join(windows_pems),
               encoding="utf-8")
print(f"Wrote {out} ({len(windows_pems)} Windows certificates added)")
