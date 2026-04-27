# Injector UI

Auxiliary FastAPI tenant upload portal. The main reproducible evaluation path
uses CLI upload scripts so every command and response is visible in the
terminal:

```bash
./scripts/test/pcap_upload.sh --csv -d data/samples/csv/ddos.csv -t tenant_A
```

Run:

```bash
./scripts/demo/run_injector_ui.sh
```

Open:

```text
http://localhost:7000
```

PCAP sample upload is also available:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/ddos.pcap -t tenant_A
```
