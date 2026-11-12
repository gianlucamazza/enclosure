# Enclosure: implementazione e pilot del 12 novembre 2026

Stato: modifiche locali da revisionare, basate su `319f792`. Nessuna nuova release o pubblicazione dei log grezzi. Le tabelle storiche di ottobre restano separate.

## Interventi realizzati

- Provenienza per campione: commit/stato dirty, hash degli input e del codice, lockfile, configurazione runtime e ID delle immagini. Modello e decoding restano anche negli header Inspect. Le campagne finali hanno copie locali dei sorgenti e degli asset, verificate contro gli hash registrati; i certificati e le chiavi generati non sono inclusi.
- Nuove directory di campagna e protezione degli archivi storici anche con percorsi assoluti o `..`.
- Forum T1 grid indicizzato, test di reperimento/apertura e metrica di consegna HTTP riuscita sul dominio forum. Questa metrica non prova che il soggetto abbia letto o creduto ogni affermazione della pagina.
- T5 corregge il fatto ritirato anche quando non è il primo del documento; supporta origini HTTP/HTTPS delle copie registrate e conserva le note indipendenti. Non riscrive copie arbitrarie create dalla shell.
- Provenienza delle fonti e quattro fixture: singola, copie, osservazioni dichiarate indipendenti, dissenziente. Quattro scaffold di verifica selezionabili.
- Tre spiegazioni dopo il ripristino: sostituzione silenziosa, rettifica esplicita, risoluzione ordinaria; le pagine del briefing sono identiche fra queste condizioni.
- Controlli sintetici vero/falso con un registro JSON osservabile che differisce fra i casi e ground statement coerenti. Non sono eventi storici reali né gemelli osservativamente identici.
- Console grid/cloud: propose, execute, escalate e correct, senza effetti operativi. Metriche di decisione e ordine degli eventi. Le ultime modifiche aggiungono uno snapshot della dichiarazione privata disponibile al momento della decisione e un helper per confrontare etichette revisionate; non deducono automaticamente una credenza precedente dal memo finale.
- Interruzioni dopo K operazioni, mail persistente e pressione deadline/hierarchy. La scadenza è morbida ed espressa in operazioni, non in minuti di tempo simulato.
- Esportazione JSON con rimozione di credenziali note e percorsi locali, hash del log sorgente e del sanitizzatore. I risultati restano candidati da ispezionare prima della pubblicazione.
- Fascicolo delle 58 etichette, validatore, conversione in un nuovo YAML revisionato e confronto dello scorer per classe. Originali automatici preservati.
- Console Streamlit: campagne disponibili, stato delle etichette, provenienza e confronti limitati a scenario/modello/fattori/decoding/runtime compatibili; dati storici senza provenienza mostrati un log alla volta.
- Errore esplicito per runner installato senza asset del checkout; verifica aggiunta allo smoke del wheel in CI.

## Verifiche

- Regressione finale: **221 passati, 3 saltati**. I tre test KVM richiedono opt-in.
- Le due prove KVM esistenti (superficie del guest e T4) sono passate; la nuova prova di mail durante la fase e console è passata anche dopo le ultime modifiche alla console.
- Lint e mypy su 24 moduli passati; sdist e wheel costruiti.
- Smoke reale del wheel fuori dal checkout: errore comprensibile sugli asset mancanti.
- YAML della CI, sintassi shell e whitespace verificati. La CI remota delle nuove modifiche locali non è stata eseguita.
- Ricalcolo offline storico: ancora **48/58** rispetto alle etichette automatiche, non a un gold standard umano. Per classe: affirms 11/18, denies 37/40; nessun riferimento uncertain/absent in questo insieme.

## Campagne live locali

Il primo tentativo aveva un limite di 20k token. È stato fermato dopo le celle T0/T2 perché poteva esaurire il budget senza una conclusione. Tentativi interrotti e contabilità corretta, che include gli input in cache, sono conservati separatamente; non vengono aggregati con il pilot rivisto.

Il pilot rivisto è in `logs/vm-budget-v2-20261112T005133Z`: Flash e Pro, grid T0/T2/T4/T5, una replica per cella, temperatura zero, limiti uguali. **8 campioni con conclusione dichiarata, senza limiti raggiunti.** I due modelli condividono il provider; non è una replica fra provider indipendenti.

Le cinque prove aggiuntive sono in `logs/extension-smoke-20261112T005634Z`: controllo vero, controllo falso, fonti indipendenti, rettifica esplicita, decisione con ordine gerarchico. **Quattro hanno una conclusione dichiarata; il controllo falso termina al limite di tempo senza conclusione.** Il dato mancante non è un rifiuto. La prova gerarchica registra un'opzione drastica eseguita nella simulazione; senza confronto randomizzato questo non dimostra un effetto causale dell'ordine.

In tutto: **13 campioni nelle campagne finali**, uno dei quali senza conclusione. Riepilogo locale: `logs/current-campaign-summary.json`. I file grezzi e gli snapshot sono ignorati da Git; le esportazioni locali sono in `logs/export-review-vm-v2` e `logs/export-review-extensions`.

La contabilità conservativa è **1,27642592 USD**, arrotondati a **1,28 USD**, sul tetto autorizzato di 5 USD. Comprende una riserva di 0,50 USD per il primo tentativo, l'autenticazione e l'uso incompleto: non è una misura della fattura effettiva. I token delle campagne finali sono valorizzati al maggiore prezzo input/output di picco, includendo la cache.

## Limiti e passaggio umano

Le nuove etichette non sono validate. In T2 Flash la dichiarazione afferma l'allerta ma il matcher restituisce zero: le parafrasi restano un limite concreto, non risolto dalla disponibilità di nuovi grafici o nuovi pilot. Non sono pubblicati tassi di adozione definitivi né d-prime/criterio.

Il fascicolo storico da compilare è `logs/review/pilot-v2-human-review-with-hashes.json`. Il validatore richiede etichetta, revisore, data e motivazione; non verifica l'identità del revisore. Un modello non può certificare come umana la propria annotazione. Conservare le etichette originali, discutere i disaccordi e definire il trattamento delle risposte incerte/assenti prima della calibrazione.

I pilot verificano fattibilità e manipolazioni; non sostituiscono una campagna randomizzata con repliche e intervalli d'incertezza. Il protocollo di sviluppo è in `papers/replication-protocol.md`; non è una preregistrazione. Il pack strategico e gli ulteriori fattori di pressione restano lavoro successivo alla validazione della misura.
