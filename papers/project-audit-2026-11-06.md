# Audit di Enclosure e priorità di sviluppo

Data: 6 novembre 2026. Revisione analizzata: `1383b3b`.

## Issue e stato del backlog

Il backlog è pubblicato su GitHub. Le issue restano aperte: la VM è implementata e verificata localmente in questa revisione, mentre la validazione CI remota è tracciata in #36. I risultati live storici non cambiano.

| Rilievo | Issue | Stato al 6 novembre 2026 |
|---|---|---|
| A1 | [#32 Validate belief scoring against human-reviewed labels](https://github.com/gianlucamazza/enclosure/issues/32) | Aperto |
| A2 | [#33 Define an identifiable truth-factor estimand](https://github.com/gianlucamazza/enclosure/issues/33) | Aperto |
| A3 | [#34 Make the T1 grid forum discoverable and measure actual exposure](https://github.com/gianlucamazza/enclosure/issues/34) | Aperto |
| A4 | [#35 Record run provenance and keep new runtime logs out of historical waves](https://github.com/gianlucamazza/enclosure/issues/35) | Aperto |
| A5 | [#36 Publish and validate the KVM subject runtime](https://github.com/gianlucamazza/enclosure/issues/36) | Implementato in questa revisione; validazione CI remota aperta |
| A6 | [#37 Validate T5 rewriting for multi-fact documents and saved copies](https://github.com/gianlucamazza/enclosure/issues/37) | Aperto |
| A7 | [#38 Add a sanitized export path for logs and sample metadata](https://github.com/gianlucamazza/enclosure/issues/38) | Aperto |
| A8 | [#39 Define a current-runtime multi-model replication protocol](https://github.com/gianlucamazza/enclosure/issues/39) | Aperto |
| A9 | [#40 Show available runs and evidence status in the analysis console](https://github.com/gianlucamazza/enclosure/issues/40) | Aperto |
| A10 | [#41 Make the installed runner asset requirements explicit and testable](https://github.com/gianlucamazza/enclosure/issues/41) | Requisito di checkout documentato; smoke installato aperto |

Le priorità scientifiche sono #32 e #33. La campagna multi-modello #39 dipende anche da provenienza #35 e pubblicazione del runtime #36. Nessuna nuova campagna live è stata avviata.

Enclosure ha una separazione chiara fra scenari, mondo controllato, strumenti e misurazione. La suite locale passa e le limitazioni dei pilot sono documentate con attenzione. Il principale blocco per conclusioni scientifiche resta la validazione della misura: il ricalcolo offline riproduce 48 accordi su 58 rispetto a etichette ancora generate da un modello. Le estensioni operative dovrebbero seguire la risoluzione di questo punto e del disegno dei controlli veri/falsi.

## Architettura e copertura sperimentale

Il flusso è YAML → `scenario.py` → `episode.py` → `times_eval.py` → strumenti e Ministry → mondo SQLite → scoring e giudice → log Inspect → script di analisi e Streamlit. `hole.py` ripristina versioni precedenti; in modalità deep riscrive file registrati con origine corrispondente alla pagina. Il transcript resta disponibile al soggetto.

| Domanda | Manipolazione e metrica | Evidenza e limite |
|---|---|---|
| Cattura della credenza | T0/T2, belief e memo separati | Pilot e wave disponibili; scorer e testi possono divergere |
| Corroborazione | T1/T2/T3, fonti consultate e adozione | Wave grid: T1 senza apertura del forum, T2 e T3 al soffitto |
| Memoria | T4/T5, revisione dopo ripristino | T4 storico; T5 senza stima live documentata |
| Conformità | Stance dei colleghi effettivamente consultati | Implementazione e test presenti, nessuna stima live documentata |
| Calibrazione | Controlli veri/falsi, hit e false alarm | Fattore truth progettato, non eseguito |
| Azioni e pressione | Decisioni simulate e verifica prima dell'azione | Disegno concordato, fuori dal runner attuale |

Pilot e wave devono restare separati: cambiano prompt, accessibilità delle fonti, temperatura e numero di repliche. Le visite alle fonti sono dati osservazionali: l'associazione fra verifica e adozione non dimostra un effetto causale della verifica.

## Rilievi e criteri di accettazione

| ID | Priorità e stato | Evidenza, conseguenza e intervento | Accettazione | Impegno |
|---|---|---|---|---|
| A1 | P0 scientifico, riprodotto | `scripts/judge_logs.py` riproduce 48/58 accordi con le label pilot. Parafrasi e formulazioni miste alterano i conteggi. Preparare un corpus con citazioni, negazioni, incertezza, assenza e risposte forzate; confrontare scorer e giudice con revisione umana. | Tutte le 58 label revisionate con autore/data, disaccordi motivati e risultati per classe; originali conservati. | Medio |
| A2 | P0 scientifico, limite del disegno | `papers/design-decisions.md` propone gemelli con evidenza identica e sola verità del ledger diversa. Senza segnale osservabile non è identificabile una capacità di discriminare quella verità. Un'eventuale differenza campionaria non dimostra discriminazione. | Specificare estimando e informazione disponibile; separare controlli storici, sensibilità all'evidenza e adozione nei gemelli. Nessuna interpretazione di d′ come accesso alla verità nascosta. | Medio |
| A3 | P1, limite documentato | README: nessuna apertura del forum T1 grid, non indicizzato. Lo 0/3 misura assegnazione senza esposizione. Rendere reperibile la fonte e registrare esposizione separatamente. | Smoke mock che trova e apre il forum; risultati distinti per assegnazione ed esposizione, senza presentare quest'ultima come confronto randomizzato. | Basso |
| A4 | P1, provenienza incompleta documentata | I pilot provengono da working tree non committati. I metadati dei campioni includono fattori ma non bastano a ricostruire tutti gli artefatti storici. | Nuove run con manifest di commit e stato dirty, hash scenari/prompt, lockfile, digest immagini, modello, decoding e versione scorer; storico marcato incompleto. | Medio |
| A5 | P1, confondente riprodotto | Il test Docker `test_subject_image_hides_ministry_strings` fallisce: subject del certificato `CN=Ministry Lab CA`. Clock, TLS e interprete sono ulteriori indizi documentati. Le fonti mancanti cambiano il trattamento effettivo. | Inventario delle anomalie per release e controllo dei link per trattamento; distinguere riconoscimento del laboratorio da rifiuto della falsa affermazione. | Medio |
| A6 | P1, ipotesi tecnica da verificare | `_hole_derived_fs` in `hole.py` usa `http_doc.fact_ids[0]` per cercare il predecessore, anziché ricevere il fact_id ritirato. Possibile errore con documenti multifatto. Inoltre l'origine è confrontata con una stringa HTTP esatta. | Test multifatto che ritira un fatto diverso dal primo; test origine HTTP/HTTPS e copie create da shell. Dichiarare quali copie T5 può effettivamente riscrivere. | Medio |
| A7 | P1, rischio da verificare | `times_eval.py` inserisce un token per campione nei metadati. Token casuali sono una protezione presente, ma i metadati richiedono controllo prima di pubblicare i log. | Esportazione pubblicabile con token e account rimossi, mantenendo traceability; test che il soggetto non legge il token né accede al control plane. | Medio |
| A8 | P1, limite inferenziale | Un solo modello con risultati, poche repliche e copertura incompleta; T2/T3 grid entrambi 3/3. | Protocollo preregistrato con più modelli, budget e decoding comparabili, intervalli d'incertezza e scenari senza effetto soffitto; autenticazione verificata prima della campagna. | Alto |
| A10 | P1, packaging verificato | Il wheel costruito contiene zero YAML; `times_eval.py` risolve `evals/compose.yaml` dalla radice ricavata dal modulo. L’installazione wheel da sola non fornisce gli asset del runner. | Smoke fuori dal checkout che carica uno scenario e risolve Compose, oppure documentazione esplicita del requisito di checkout con comando supportato. | Medio |
| A9 | P2, usabilità | Streamlit mostra campioni e score, ma il default `logs/matrix` differisce dalle directory delle evidenze pubblicate. I risultati richiedono contesto su label e provenienza. | Selettore delle run disponibili; stato delle label, versione scorer e avviso di non comparabilità visibili accanto ai risultati. | Basso |

P0 indica un blocco alla validità delle conclusioni, non una vulnerabilità critica accertata. Nessuna vulnerabilità di isolamento viene dichiarata confermata da sola lettura del codice.

## Isolamento e riproducibilità

Sono presenti rete Docker interna per il soggetto, binding loopback dello stack lab, token per campione, confronto del token a tempo costante, controllo dei percorsi scenario e immagini base fissate per digest. La CI include unit test, typecheck, build, installazione wheel ed end-to-end Docker; il controllo di formattazione è informativo.

Lo stack lab collega Ministry anche a una seconda rete: verificare che gli endpoint raggiungibili dal soggetto non fungano da proxy verso l'esterno. I test di accettazione devono includere richieste senza token, percorsi fuori root e symlink, host non previsti, uscita di rete e due campioni consecutivi con stato distinto. Il percorso da wheel deve provare anche il caricamento degli scenari, oltre a `--help`.

Il virtualenv locale conteneva un collegamento a un interprete inesistente. `uv run --locked --group dev` lo ha ricreato con Python 3.12.15 senza cambiare lockfile. Questo era un problema dell'ambiente locale, non un fallimento della suite.

## Nuovi casi d'uso e sequenza

| Caso d'uso | Esperimento minimo | Metrica e dipendenza |
|---|---|---|
| Strategie di verifica | Stesso scenario con scaffold standard e verifica indipendente prescritta | Adozione falsa e accettazione vera; richiede A1/A2 |
| RAG con fonti correlate | Più documenti dello stesso editore contro fonti realmente indipendenti | Sensibilità alla provenienza; aggiungere provenienza ai fixture |
| Correzioni e memoria persistente | Rettifica dopo salvataggio di note e copie | Correzione, conservazione della cronologia, errori residui; richiede A6 |
| Conformità sociale | Maggioranza, dissenso e fonti condivise a documenti costanti | Credenza privata contro memo; verificare interlocutori realmente consultati |
| Regressioni di prompt e scaffold | Corpus congelato prima e dopo una modifica | Variazione per episodio con incertezza; richiede A4 |
| Decisioni operative simulate | Grid/cloud con propose, execute ed escalate registrati | Azione drastica, verifica prima dell'azione, escalation umana; dopo A1/A2 |

Ordine consigliato: validazione delle label e del disegno truth → esposizione e provenienza → copertura dei trattamenti e secondo modello → confronti degli scaffold → interruzioni, azioni e pressione nella sequenza già concordata. Il pack strategico resta successivo alla validazione dell'action layer. Nessuna azione della console deve produrre effetti operativi reali.

## Verifiche riproducibili

- `uv run ruff check src tests evals`: superato.
- `uv run --locked --group dev pytest -q --ignore=tests/test_times_inspect.py --ignore=tests/test_subject_tells.py`: 196 test superati in 61,93 secondi.
- `uv run python scripts/judge_logs.py logs/pilot-v2 --labels papers/labels/pilot-v2.yaml`: 48/58 accordi, dieci disaccordi riprodotti; nessun giudice remoto chiamato.
- `uv run mypy`: superato, 17 file sorgente.
- `uv build`: sdist e wheel costruiti; ispezione ZIP del wheel: zero file YAML.
- `uv run pytest -q tests/test_times_inspect.py tests/test_subject_tells.py`: 3 passati e 1 fallito in 421,57 secondi. Passano T0 mock, ripristino T4 e uscita dopo esaurimento budget. Fallisce il controllo del subject CA, che contiene `Ministry Lab CA`. L’esito riguarda il certificato locale riutilizzato dalla build; la rigenerazione da ambiente pulito non è stata provata.

Il controllo offline estrae gli ultimi `write_file` per nome file e applica le rubriche correnti: è un ricalcolo con il codice attuale, non una ricostruzione dell'ambiente storico. La validazione umana delle label rimane aperta e non è sostituita dall'audit automatico.

## Correzioni successive all’audit

Il generatore della CA ora riusa soltanto certificati con subject neutro, SAN aggiornati, validità alla data del desk e almeno un giorno di validità residua e chiave privata valida e corrispondente. Le coppie precedenti sono sostituite dopo la generazione riuscita. Il nome del servizio di controllo `ministry` resta nella rete interna, ma non compare più nei SAN. I nuovi certificati coprono il periodo 2020–2036 per includere il desk del 2026 anche quando vengono generati successivamente. Curl e Python non disabilitano più la verifica TLS; usano la CA installata nell’immagine.

I test di regressione verificano migrazione da `Ministry Lab CA`, riuso della coppia valida, recupero da chiave corrotta e assenza del servizio nei SAN. Dopo le modifiche: 198 test locali superati e lint superato.

Queste correzioni riducono gli indizi, senza rendere il mondo indistinguibile da Internet. Restano ispezionabili il preload del clock, i wrapper e gli hook Python, la rete Docker, il gateway unico e il certificato condiviso fra domini indipendenti. La shell può inoltre confrontare il clock simulato con altre sorgenti locali. L’obiettivo di non riconoscibilità richiede un profilo di minaccia esplicito: per soggetti con shell arbitraria, la soluzione architetturale da validare è una VM con clock coerente, rete e DNS simulati fuori dal guest, certificati per host e control plane separato. Rinominare questi artefatti non risolve il problema. Le run attuali devono restare descritte come rilevabili.

Verifica finale delle correzioni: tutti e quattro gli end-to-end Docker superati in 136,13 secondi, inclusi fetch HTTPS con verifica attiva, ripristino T4, uscita a budget esaurito e controllo dell’immagine. Typecheck superato su 17 file; lint e `git diff --check` superati. Le verifiche della sezione originale descrivono lo stato prima delle correzioni.

## Backend VM implementato

Le nuove task Times e Wire usano ora `backend=vm`; `backend=docker` conserva il percorso legacy. Il provider Inspect `enclosure_vm` esegue ogni operazione del soggetto in un guest Linux QEMU/KVM, con UID 1000. Il controller usa Docker per il lifecycle, KVM e TUN come dispositivi e NET_ADMIN soltanto nel proprio namespace. Ogni campione ha disco, chiavi e workspace nuovi; non esiste fallback al controller quando la VM fallisce.

Il clock parte dalla data dello scenario nell’RTC virtuale e avanza normalmente. DNS UDP/TCP e TLS per dominio sono serviti fuori dal guest su una TAP. Il firewall nega il forwarding e il proxy nega `/inner/`; chiavi TLS, token e codice del controller non entrano nel guest. I file piantati sono sincronizzati per contenuto, senza mount condivisi; le note indipendenti del soggetto persistono attraverso T4.

Verifiche finali:

- Suite predefinita: **204 passati, 2 saltati** in 73,78 secondi. I due test VM richiedono opt-in esplicito per KVM.
- `ENCLOSURE_VM_TESTS=1 uv run pytest -xq tests/test_vm_inspect.py`: **2 passati** in 150,49 secondi.
- La prova VM esegue shell/Python nel guest e verifica UID, assenza di preload/hook/file di instradamento, clock di kernel coerente, DNS, certificati distinti e verificabili, control plane negato ed egress pubblico negato.
- La prova T4 verifica aggiornamento del file NEWS e conservazione delle note del soggetto.
- La sonda `scripts/check_subject_surface.py --vm-container <controller>` restituisce `findings: []` nel guest; il container legacy aveva dieci rilievi.
- Lint, mypy su 18 sorgenti, parsing YAML e controllo whitespace superati. Container, rete e volume del progetto di debug sono stati rimossi.

La non riconoscibilità è circoscritta agli artefatti verificati. QEMU, una CA aziendale, DNS sintetico, rete limitata e contenuti authored restano inferibili; riconoscere una normale VM non equivale a identificare Enclosure. La CI include un job KVM dedicato. Le nuove run non vanno aggregate con quelle legacy, poiché cambiano clock, privilegi e trasporto.
