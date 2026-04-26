# Injector UI

Future/optional FastAPI tenant portal. It is kept in the repository for later
UI work, but the current presentation demo uses CLI upload for reliability:

```bash
./scripts/test/pcap_upload.sh -d data/samples/pcap/cic_attack_sample.pcap -t tenant_A
```

Run:

```bash
./scripts/demo/run_injector_ui.sh
```

Open:

```text
http://localhost:7000
```

Create the two demo PCAP samples first if they do not exist:

```bash
./scripts/test/create_cic_pcap_samples.sh
```
