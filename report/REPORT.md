# Translator Assignment Recommendation System (TARS)
### Project Report — Team 9

---

## Abstract

This project builds a recommendation system that helps the project managers (PMs) at iDisk assign the right translator to each incoming task.
The company runs a 24/7 operation and handles about 70,000 tasks per year, and
the decision of who works on each task is made manually, a process that consumes
roughly 30,000 PM hours annually and depends on each manager's personal memory and
judgment. Our system
takes the description of an incoming task — the client, the language pair, the time window,
the deadline and the task type — and returns a ranked shortlist of translators who can
realistically take it on, together with the reasons behind each suggestion.

The recomendation system works in two stages. First, a constraint engine filters out every translator who
cannot do the task because of a hard limitation: the wrong language pair, no availability,
a rate above the client's budget, a quality history below the client's minimum, or no
experience in the relevant field. When no perfect candidate exists, the engine relaxes the
requirements gradually and in a controlled order, mirroring how a human PM compromises in
practice. Second, a scoring step ranks the remaining candidates along the dimensions that
matter — quality, punctuality, cost and experience — with the emphasis shifting according
to what each client values most. We implemented two rankers for this: a transparent
rule-based weighted score and a machine-learning model.

This report describes the problem and its business context, the data we worked with and
what we learned from analysing it, the technical design of our solution, the business value
it offers, the difficulties we encountered and how we approached them, the way we organised
ourselves as a team, and finally an assessment of how the solution helps people,
where it falls short, and what we would do differently if we started again.

---

## 1. Introduction

### 1.1 Context

Translation companies operate as a marketplace between clients who need content translated
and a pool of translators with different skills, languages, rates, schedules and track
records. The company behind this project manages a very large volume of work — around
70,000 tasks per year — across many language pairs, many clients and many task types, and
it does so around the clock. Behind every one of those tasks sits a small but real decision:
who should do it?

### 1.2 The problem

Choosing a translator for a task is a constrained matching problem with several
objectives. The translator must:

- **cover the language pair** of the task (for example, English into Spanish);
- **be available** during the time window and have enough capacity to finish before the
  deadline;
- **fit the client's budget** — their hourly rate must be acceptable given what the client
  pays;
- **meet the client's quality requirements** — some clients impose a minimum quality level;
- ideally, **have experience** in the client's industry or in the specific type of task.

On top of these constraints, different clients have different priorities. Some are most
sensitive to price, some to quality, and some to meeting the deadline. A good assignment is
not simply the "best" translator in the abstract, it is the translator who best fits *this*
task for *this* client under *these* priorities, without wasting a good translator on a
routine job or putting an underqualified person on a hard one.

Today this matching is done manually. For each task, a PM relies on experience to
decide who is suitable, and then assigns the work. At the company's scale, this is:

- **Expensive** — about 30,000 PM hours per year are spent on assignment decisions that are
  largely repetitive.
- **Inconsistent** — two PMs may handle the same task differently, and decisions reflect
  individual habits rather than the company's full history of what has actually worked.
- **Hard to scale** — as volume grows, the manual approach does not.

### 1.3 Objective

Our objective was to build a system that, given a new task, **recommends the translators
who best fit it** while doing so, quickly, consistently, transparently, and on the basis of the company's
real historical data. The system is explicitly designed to *support* the PM rather than
replace them: it produces a ranked, explained shortlist, and the PM keeps the final
decision. This keeps a human accountable for the outcome and makes the tool realistic to
use in practice.

---

## 2. The Data

Understanding the data was both the starting point and one of the hardest parts of the
project, so we describe it in some detail here.

### 2.1 Sources

The company provided four datasets (originally four sheets of a single workbook):

- **Task history (`Data`)** — the central log of past tasks. Each row records the project
  and task identifiers, the responsible PM team, the planned start and delivery times, the
  task type, the source and target languages, the assigned translator, a series of workflow
  timestamps (when the task was pre-assigned, when the translator was told to start, when
  they began working, when they delivered, when the PM received and closed it), the hours
  worked, the translator's rate, the total cost, a quality evaluation score, and a four-level
  classification of the client's industry (sector, industry group, industry, sub-industry).
- **Schedules (`Schedules`)** — each translator's working hours (start and end of their
  workday) and which days of the week they work.
- **Clients (`Clients`)** — each client's selling price per hour, their minimum acceptable
  quality score, and a "wildcard" field stating which requirement (quality or price) may be
  relaxed when no perfect match is available.
- **Translator rates and pairs (`TranslatorsCost+Pairs`)** — for each translator, which
  language pairs they cover and their hourly rate for each.

### 2.2 Scale and shape of the data

Our analysis was carried out on the full historical dataset. Its scale is substantial:

| Table | Rows | Columns |
|---|---|---|
| Task history | 997,933 | 29 |
| Schedules | 983 | 11 |
| Clients | 2,645 | 6 |
| Translator rates and pairs | 4,688 | 7 |

In total the history covers nearly **one million tasks** spread across about **13,692
projects**, handled by **4 PM teams**, performed by **983 translators**, for **2,645
clients**, across **13 task types**.

The data is highly concentrated in several ways, which has direct consequences for the
system:

- **Task types** — proofreading (about 43%) and translation (about 40%) together make up
  roughly 83% of all work. The remaining types (post-editing, miscellaneous, engineering,
  language lead, management, DTP, test, spotcheck, training, and a few others) form a long
  tail.
- **Languages** — the work is mostly from English: English is the source language
  in about 97% of tasks. Then the target, Spanish (Iberian) is about 49%
  of tasks, followed by Galician, Catalan, Spanish (Latin America) and Basque.
- **Language pairs** — the pair English → Spanish (Iberian) represents about 47% of
  all tasks. The translation work is therefore mostly a few pairs, and a lot of rare ones.
- **Clients** — the top two clients alone account for about 43% of all tasks, and the top
  five for roughly 56%. Two industry sectors (Information Technology and Communication
  Services) together represent about 70% of the work.
- **Translators** — workload is very unevenly distributed. The most active translator alone
  did about 6.5% of all tasks, and the top twenty translators together did close to half of
  all the work.

Every task is scored on quality on a 0–10 scale, with a mean of about 7.0 and a standard deviation of
about 1.5. Translator hourly rates range from 8 to 62, with a typical
value around 16–17 on the task records. Clients' selling prices range from 20 to 50 (median
35), and the selling price is, on average, roughly double the translator cost rate, which is
where the company's margin comes from.

### 2.3 Data quality

The historical data, being real and accumulated over more than a decade, contained a number
of inconsistencies that we had to identify and handle. The most important findings were:

- **Out-of-order timestamps** — about 3.7% of tasks (around 36,800 rows) had a start time
  recorded as *later* than the end time. The other workflow steps (pre-assigned → ready →
  working → delivered) were consistent.
- **Zero-value tasks** — about 7% of tasks (around 69,000 rows) recorded zero hours worked
  *and* zero cost, mostly in proofreading.
- **Outliers** — hours worked ranged up to 725 in a single record and cost up to about
  14,000, far above the typical values (median hours around 0.3, median cost around 5).
- **Same-language tasks** — about 0.16% of tasks had the same source and target language,
  which is not a normal translation.
- **Impossible dates** — isolated records dated 1956 and 2050 clearly are not correct.
- **Encoding artefacts** — some names and language labels carried character-encoding
  problems (for example, accented characters rendered incorrectly).
- **Missing values** — these were, by contrast, almost negligible: only a handful of rows
  were missing cost, rate or timestamps, and there were no exact duplicate rows in any table.

A reassuring finding was that the four datasets join together almost perfectly: essentially
every task in the history matched a client, a schedule and a rate record, with only five
translator/language-pair combinations failing to match (and those were traced to spelling
variants rather than genuinely missing data). This meant we could combine the sources with
confidence.

### 2.4 Relationships in the data

Beyond describing the data, we studied how the variables relate to each other, since this
directly informs what a recommendation model can and cannot do.

- **Cost does not buy quality.** The correlation between a translator's rate and the quality
  score of their work is essentially zero (about −0.01). Paying more does not lead to better results.
- **Quality is hard to predict.** None of the available features carry much signal about the
  quality of a future task. The best predictors are a translator's *prior average quality*
  (on similar task types, language pairs, or overall), but even these are weak.
- **Quality and punctuality are largely independent.** Being on time and producing
  high-quality work are almost unrelated (correlation about 0.02 at the task level). This is
  an important finding: it means the system should treat these as two separate dimensions
  rather than assuming a "good" translator is good on both at once.
- **Some engineered features were redundant or degenerate.** Several candidate features
  turned out to be perfectly correlated with each other (for example, two different ways of
  computing margin), or constant across all rows, so they provided no information.

### 2.5 New translators

At the begining, we also worried about new entities with no history. But 
we found that this was not really the issue: there were essentially **no translators with
zero history**. The real problem was **sparse history**, a few hundred translators had only
a handful of scored tasks, which makes their estimates unreliable. We also found
that a translator's quality estimate tends to stabilise after only a small number of tasks
(a median of about four), though some take many more. This changed our perspective from how 
to handle the absence of a translator's record, to how much to trust a track record with few tasks.

### 2.6 The five recommendation dimensions

From all of the above, we settled on five dimensions that capture what makes a translator a
good fit for a task, and which the system is built around:

1. **Experience** — accumulated hours working for the client, the client's sector or
   industry, and the task type.
2. **Quality** — the translator's historical quality evaluation scores.
3. **Punctuality** — how reliably the translator delivers on time.
4. **Cost** — the translator's rate against the client's budget (the margin).
5. **Availability** — whether the translator's schedule fits the task's time window and
   deadline.

---

## 3. Our Solution: Technical Design

### 3.1 Overview

The system is structured as a pipeline that turns the raw company data into a ranked,
explained recommendation for a given task. It separates **offline data preparation** (done
once, ahead of time) from the **online recommendation flow** (run for each task), so that
the live response is fast. The main components are: a data-preparation stage, a
feature-building stage, a constraint engine, a ranking step, an output formatter, a backend
service that exposes the system over the web, a front-end interface for PMs, and an
evaluation script for measuring quality.

### 3.2 Data preparation

The raw workbook is first converted into clean per-table CSV files, and then into a set of
processed tables that the system reads at run time. The preparation cleans the task history
— parsing all the timestamps, computing how long each task actually took, deriving an
on-time flag by comparing the planned deadline with the actual delivery time, and dropping
rows that are internally inconsistent — and then produces a per-translator statistics table.
We deliberately keep the raw data untouched and write all transformations into separate
intermediate and processed folders, so the whole process can be re-run from scratch and so
that it is always clear which data is raw, which is in progress, and which is final. A single
bootstrap script sets up the environment and builds these tables, so a new team member can
get a working copy from a clean checkout.

### 3.3 Feature building

The processed translator statistics table is the heart of what the recommendation engine
reads. For each translator it brings together, from the four data sources:

- their hourly rate for each language pair they cover;
- their **average quality** score across all their scored tasks;
- their **on-time score** — the fraction of their tasks delivered on time;
- their **experience** broken down by task type (for example, total hours of proofreading,
  of translation, and so on); and
- their **experience by industry**, computed at three levels — sub-industry, industry, and
  industry group — so that the system can look for a specialist first and broaden out if
  needed.

This hierarchical view of experience is what lets the engine reason about expertise at
different levels of specificity, which becomes important in the relaxation logic below.

### 3.4 The constraint engine

The core of the system is a decision engine that, given a task, decides which translators
are eligible. It first looks up the client's requirements — their budget (derived from the
selling price), their minimum quality, their wildcard preference — and works out which
industries are relevant from the client's own history, as well as the delivery window
implied by the dates. It then applies a series of **hard constraints** that remove
translators who cannot do the task:

- they do not cover the required language pair;
- their rate exceeds the client's budget;
- their average quality is below the client's minimum;
- their on-time score is below the client's threshold;
- they do not work on the required days, or their shift does not provide enough daily
  capacity to finish the work before the deadline;
- they have no experience in the required field.

Some **task types change these rules**, reflecting real business policies:

- **Test tasks** ignore the budget entirely and select on quality — the goal is to identify
  the best possible translator regardless of cost.
- **Training tasks** drop the quality and experience requirements, since the point is to
  develop a translator rather than to use an already-expert one.
- **Translation followed by proofreading** relaxes the quality threshold slightly, since the
  proofreading step will catch issues.
- **Proofreading and spotcheck tasks** must go to a *different* and *more experienced*
  translator than the one who did the previous step, since a review should be done by someone
  at least as capable.

### 3.5 Graceful relaxation

In a marketplace this constrained, it frequently happens that *no* translator satisfies every
hard requirement. A naive system would simply return "no match". Instead, our engine relaxes
the requirements step by step, in a deliberate order, stopping as soon as candidates appear:

1. **Strict** — look for a specialist who matches at the narrowest level (sub-industry).
2. **Broaden expertise** — if none, accept experience at the wider industry level, then at
   the whole industry-group level.
3. **Apply the client's wildcard** — relax the single dimension the client said it cares
   least about. A *quality* wildcard lowers the minimum quality; a *price* wildcard raises the
   budget by 25%; a *deadline* wildcard eases the on-time and scheduling requirements.
4. **Global relaxation** — as a last resort, loosen the remaining constraints.

This ordering matters: it encodes the idea that we would rather find a slightly less
specialised translator than violate the client's stated priority, and that we only sacrifice
the client's priority dimension as a true last resort. It mirrors how an experienced PM
reasons through a difficult assignment, and — importantly — when it does relax something, the
system records what it relaxed, so the recommendation can be explained honestly.

### 3.6 Task splitting

If even relaxation fails to find a single suitable translator — typically because the task is
too large to finish in time for one person — the engine tries to split the work:

- **Across days** — give the task to one translator who has enough daily capacity to finish it
  over the available window, rather than requiring it all in one shift.
- **Across translators** — assign several translators to work on it in parallel, dividing the
  required hours among them.

This lets the system handle large or urgent tasks that no individual could absorb alone.

### 3.7 Ranking: the rule-based scorer

Once the engine has produced a set of eligible translators, they need to be ordered. Our
first ranker is a transparent rule-based score out of 100, combining four normalised
components — quality, reliability (on-time record), cost margin, and experience — with weights
that shift according to the client's wildcard:

| Mode | Quality | Reliability | Margin | Experience |
|---|---|---|---|---|
| Balanced (default) | 40 | 30 | 20 | 10 |
| Quality-sensitive | 60 | 20 | 10 | 10 |
| Price-sensitive | 20 | 20 | 50 | 10 |
| Deadline-sensitive | 20 | 60 | 10 | 10 |
| Test task | 80 | 0 | 0 | 20 |

A notable design choice is what we call **resource conservation**. Outside of explicitly
quality-driven cases, the scorer does not simply reward the highest quality and the most
experience. Instead, it rewards a *good enough* fit: a translator who comfortably clears the
client's requirements scores higher than one who massively exceeds them. The reasoning is
practical — putting the company's most expert, highest-quality translators on routine tasks
"wastes" them, when they could be reserved for the demanding work that actually needs them.
This is a deliberate business stance rather than a pure "best translator wins" approach, and
it is one of the points we would want to validate carefully with the company.

### 3.8 Ranking: the machine-learning model

Our second ranker is a machine-learning model — a gradient-boosted regression model — that
predicts an "efficiency" score for each eligible candidate based on features such as the
client's budget and required quality, the translator's quality, on-time record and rate, and
the gaps between them. The intention was the same "good fit, not overkill" idea expressed as a
learned function rather than fixed weights, so that the relative importance of each factor
could be inferred from data rather than set by hand. Both rankers consume the same eligible
set, so the constraint logic is shared and only the final ordering differs.

### 3.9 Output and explainability

Whichever ranker is used, the system returns the top recommendations (by default the top ten)
as a table in which each row carries not just the translator and the score, but the underlying
values: their rate for the language pair, their daily capacity, their average quality, their
on-time score, and the relevant experience figure. This is central to the product: the PM does
not just see *who* is recommended, but *why*, and can therefore trust or overrule the
suggestion with full information.

### 3.10 The backend service

To make the system usable from a web interface, we built a backend service that exposes it
over HTTP. It offers an endpoint that takes a task's parameters and returns the ranked
recommendations, plus a set of endpoints that let the interface browse the underlying data —
translators, clients, tasks and schedules — with pagination. The recommendation results are
returned in a clean structured form, including the requirements the system derived for the
task, so the front-end can display the full rationale.

### 3.11 The web interface

The front-end is a web application aimed at project managers, built with a modern JavaScript
framework. It provides a dashboard and dedicated views for assigning a task, comparing
translators, and browsing the translators, clients and tasks in the system. The interface
communicates with the backend only through the service described above, keeping a clean
separation between the user interface and the recommendation logic, so that either side can
evolve independently.

### 3.12 Evaluation

To judge whether the recommendations are actually good, we wrote a backtesting script. It
takes historical tasks, hides the translator who was really chosen, runs the full system on
the task, and checks where the real translator appears in the recommended list. From this we
can compute concrete measures: how often the real translator is in the top *N* (the hit rate),
how often they appear among the eligible candidates at all (recall), and their average rank
when they do. This gives an objective, data-grounded way to track whether changes to the
system make it better or worse, rather than relying on intuition.

### 3.13 Reproducibility and deployment

The whole project is set up to be reproducible. A single bootstrap script creates a clean
environment, installs the dependencies, and builds the data tables the system needs, so that
a fresh copy of the repository can be made to run with one command. The web interface and the
backend can be brought up together for development, and the data flow — from raw files, to
intermediate CSVs, to the final processed tables the system reads — is documented and
scripted end to end.

---

## 4. Our Solution: Business (B2B) Perspective

Technically, TARS is a recommendation pipeline. Commercially, it is a **decision-support tool
for project managers** that targets one of the company's largest hidden costs: the time and
inconsistency of manual assignment. Its value can be summarised along four lines.

**Speed and cost.** The company spends on the order of 30,000 PM hours a year on assignment.
By replacing the manual search with an instant ranked shortlist, TARS removes the bulk of
that repetitive effort, letting PMs handle more tasks in less time and freeing them for the
decisions that genuinely require human judgment.

**Consistency and institutional memory.** Because the system evaluates every task the same way
and on the basis of the company's entire history, it removes the variation that comes from
different managers making different calls, and it captures knowledge — who is good at what —
that would otherwise live only in individuals' heads and leave with them.

**Client-aware flexibility.** The wildcard mechanism means the system reflects what each client
actually values. A price-sensitive client and a quality-sensitive client asking for the same
task will get appropriately different recommendations. This aligns the tool with the commercial
reality that not all clients want the same thing, and it does so automatically.

**Trust through explainability.** Every recommendation is accompanied by the figures behind it,
and the system is honest about when it has had to relax a requirement to find a candidate.
This transparency is what makes the difference between a tool PMs actually use and a black box
they ignore. It also keeps a human firmly in control: TARS proposes, the PM decides.

Taken together, this positions TARS not as an automation that removes the PM, but as a force
multiplier that makes each PM faster, more consistent, and better informed — which is also what
makes it realistic to roll out in a real operation, where accountability and trust matter as
much as raw accuracy.

---

## 5. Difficulties Encountered and How We Approached Them

### 5.1 Messy real-world data

By far the biggest challenge was the data. A decade of accumulated records contained the
inconsistencies described in Section 2.3 — out-of-order timestamps, zero-value tasks, extreme
outliers, impossible dates, encoding problems. None of these were obvious until we looked, and
each one forced a decision about whether to drop, correct, or simply flag the affected rows.
Our approach was to make the data-quality analysis the *first* piece of work, write it up
clearly, and treat its conclusions as the shared foundation everyone else built on. That way
the rest of the team did not keep rediscovering the same problems independently.

### 5.2 Working at scale

Nearly a million rows is enough to cause practical problems. Some of our analysis ran out of
memory when computing certain statistics over the whole dataset at once. This pushed us toward
a more disciplined design: compute the heavy features once and store them, sample where a full
pass was not necessary, and keep the expensive preparation step strictly separate from the
fast, live recommendation step. The same discipline made the live system responsive.

### 5.3 Deciding what the system should optimise for

A more conceptual difficulty was deciding what "the best translator" even means. Our analysis
showed that quality is genuinely hard to predict and unrelated to cost, that punctuality is
much more predictable and driven by availability, and that quality and punctuality are
essentially independent of each other. These findings pushed us away from assuming a single
notion of a "good" translator and toward treating the dimensions separately, and they made us
appreciate that a clear, explainable rule-based approach was at least as defensible as a more
complex model. The "resource conservation" idea — not over-spending top talent on routine work
— also came out of thinking hard about what the company actually wants, rather than what is
easiest to optimise.

### 5.4 Keeping the pieces consistent

Because the project spans data preparation, a recommendation engine, a backend and a front-end,
a recurring difficulty was keeping these parts agreed on the same formats and assumptions, and
keeping the documentation in step with code that was still changing. We addressed this by
agreeing on a single documented data flow and a clear contract between the front-end and the
backend, so that each part could be developed independently against a stable interface.

### 5.5 Teamwork

We organised the work using an issue tracker, breaking the project into clear areas — data
analysis and feature creation, the constraint engine, the ranking models, the backend API, and
the front-end interface — and assigning owners to each. We used separate branches so that
people could work in parallel without breaking one another's code, and we kept a shared log of
key decisions (including how and where we used AI tools to help), so that everyone worked from
the same understanding of the project. The main friction was the ordinary one of integration:
making sure independently developed components fit together, and resolving the small mismatches
that appear when several people build adjacent parts at once. Splitting the work along clean
boundaries, and agreeing those boundaries early, was what kept this manageable.

---

## 6. Conclusion

### 6.1 How our solution helps people

TARS tackles a real, costly and repetitive problem. By turning translator assignment into a
fast, consistent and explainable recommendation, it gives project managers back a large amount
of time and removes much of the inconsistency of manual decisions, while grounding those
decisions in the company's own history rather than in individual memory. For the company, that
means lower operational cost and decisions that are more uniform and more defensible. For
translators, a data-driven process means work is distributed on the basis of genuine fit and
track record, rather than on which manager happens to think of them first, which is fairer. And
throughout, the system is built to assist rather than replace: it offers a transparent starting
point and leaves the final, accountable decision with a person.

### 6.2 How we could have made it better

We are clear-eyed about the system's limitations, and there are several things we would improve
with more time:

- **Ground the machine-learning model in real outcomes.** Our learned ranker currently predicts
  a designed efficiency score rather than something directly measured — like the quality
  actually delivered or whether the task was on time. Training it on real outcomes would make it
  genuinely informative and let it discover patterns the hand-set rules miss, instead of being a
  more elaborate way of reproducing a formula. Our own analysis even points the way: punctuality
  is the dimension that is actually predictable, so it is the most promising thing to learn.
- **Evaluate at full scale.** We built the backtesting framework but did not run it across the
  whole history. Producing solid hit-rate numbers would let us state with confidence how good
  the recommendations are, and would turn "we think this works" into "this works, and here is the
  evidence".
- **Simplify and unify.** A few parts of the system ended up with two parallel ways of doing the
  same thing (for instance, more than one path for reading the data). Consolidating these would
  make the project cleaner, easier to reason about, and easier to maintain.
- **Harden and test.** The most intricate logic — the relaxation and splitting fallbacks — would
  benefit from a fuller set of automated tests, and the backend would need additional robustness
  and security work before being exposed in a real deployment.
- **Validate the business assumptions.** The resource-conservation choice, and the exact numbers
  in the wildcard relaxations and ranking weights, are reasonable starting points but should be
  tuned and confirmed against what the company actually wants, ideally with PMs in the loop.

### 6.3 What we would change about the process

If we were to start the project again, we would do a few things differently. We would invest in
the data-quality analysis even earlier and treat it explicitly as the foundation for everything
else, since so many later decisions turned out to depend on understanding the data properly. We
would decide sooner what precisely we wanted the model to predict, rather than building the
modelling machinery first and questioning the target afterwards. And we would lock in the shared
data formats and the boundaries between components earlier, to reduce the integration friction
that comes from keeping independently built parts in sync. None of these are surprising lessons —
they are the normal trade-offs of building something real under time pressure — but they are the
ones we felt most directly, and the ones we would carry forward into the next project.

### 6.4 Closing

TARS demonstrates that a large, expensive, manual decision can be turned into a fast,
consistent and explainable recommendation using a company's own historical data. The result is
not a system that decides for people, but one that helps them decide better — saving time,
spreading work more fairly, and capturing institutional knowledge that would otherwise stay
locked in individual heads. There is clear room to make it more accurate and more polished, but
as a foundation it shows both the value of the idea and a realistic path to delivering it.
