<script setup lang="ts">
useHead({ title: "Method — Quince Ledger" });
</script>

<template>
  <div>
    <SiteMasthead />

    <main class="page method">
      <header class="method-hero">
        <h1>Every figure is a disclosed spread — price minus Quince&rsquo;s own reported cost.</h1>
        <p class="hero-text">
          Nothing here is inferred margin, third-party costing, or a statement about Quince&rsquo;s
          business. It is a reading of the cost breakdown printed on Quince&rsquo;s own product
          pages, kept as a dated record.
        </p>
      </header>

      <section class="method-section">
        <div class="method-heading">
          <p class="label method-kicker">THE DISCLOSURE BASIS</p>
          <h2>Where the numbers come from</h2>
        </div>
        <div class="method-prose">
          <p>
            Every ranked row is backed by a captured Quince product page. From that page the
            ledger takes two things: the listed price, and the transparent-pricing breakdown
            Quince publishes beside it — materials, crafting, packaging, freight, duties and
            fees, and the reported total they sum to.
          </p>
          <p>
            The spread is that listed price minus that reported total. A negative spread means
            the item is listed below the cost Quince discloses for it: a loss leader by that
            measure, and only that measure.
          </p>
          <p>
            <strong>What the spread does not cover.</strong> Marketing, returns, support,
            overhead, and inventory losses sit outside every breakdown Quince publishes. A
            positive spread is not proof of profit and a negative spread is not proof of a loss
            at the business level. These are disclosed figures, and they stay that way.
          </p>
        </div>
      </section>

      <section class="method-section">
        <div class="method-heading">
          <p class="label method-kicker">HOW COUNTING WORKS</p>
          <h2>Display groups and classifications</h2>
        </div>
        <div class="method-prose">
          <p>
            The catalog counts <strong>styles</strong>, not colours and sizes. One product at
            one selling price is one style; colours and sizes that share that price are counted
            together. A product sold at two prices is two styles, because the two price tiers
            are genuinely different offers.
          </p>
          <dl class="method-definitions">
            <div>
              <dt>Below cost</dt>
              <dd>Every option in the style is listed below its own reported cost.</dd>
            </div>
            <div>
              <dt>Above cost</dt>
              <dd>Every option is listed above its own reported cost.</dd>
            </div>
            <div>
              <dt>At cost</dt>
              <dd>The difference is exactly zero.</dd>
            </div>
            <div>
              <dt>Varies</dt>
              <dd>The options disagree: some below cost, some above. The catalog shows the range and says so, and never picks one answer.</dd>
            </div>
          </dl>
          <p>
            The tabs select styles, not classifications. <em>Below cost</em> lists any style
            with at least one option below cost, so a style whose options disagree appears under
            both <em>Below cost</em> and <em>Above cost</em>, each time with its full range.
          </p>
        </div>
      </section>

      <section class="method-section">
        <div class="method-heading">
          <p class="label method-kicker">IDENTITY</p>
          <h2>Products, variants, and price tiers</h2>
        </div>
        <div class="method-prose">
          <p>
            A display name is not an identity. Colours and sizes carry their own SKUs, prices,
            and cost breakdowns, so the ledger stores each observation against a
            product&nbsp;key and a variant&nbsp;key and keeps them apart. Two rows that look
            alike are never merged because they look alike.
          </p>
          <p>
            When a group covers several variants and their costs differ, the table shows the
            range — <em>$42.00–$48.00</em>, never a single figure pretending to be universal.
            Opening the group offers each variant separately, and each one keeps its own history.
          </p>
        </div>
      </section>

      <section class="method-section">
        <div class="method-heading">
          <p class="label method-kicker">THE RECORD</p>
          <h2>What a stored observation carries</h2>
        </div>
        <div class="method-prose">
          <p>
            Each crawl writes a new observation rather than editing an old one. An observation
            holds the selected price, every disclosed cost line, the derived spread and margin,
            the parser version that produced it, and the capture it came from. A price that did
            not move is still re-recorded, so the ledger can tell silence from absence.
          </p>
          <p>
            <strong>The fee guardrail.</strong> Occasionally a page reports duties, taxes, and
            fees larger than the rest of its own breakdown. When that happens the ledger sets
            that component to $0.00 for the calculated cost, marks the row with an asterisk, and
            keeps the originally disclosed amount in the record. The source value is never
            quietly dropped.
          </p>
          <p>
            Partial and internally inconsistent pages are kept as diagnostics and left out of
            the ranking. A row only appears in the table when the price, the reported total, and
            the spread are all present and agree.
          </p>
        </div>
      </section>

      <section class="method-section">
        <div class="method-heading">
          <p class="label method-kicker">THE CHANGE LEDGER</p>
          <h2>Reading what actually moved</h2>
        </div>
        <div class="method-prose">
          <p>
            Every item's page lists what changed beneath its cost breakdown. It lists
            the moves between consecutive captures in order: the price, each cost line, and the
            resulting spread, with the amounts on either side of the move.
          </p>
          <p>
            Each move carries a signed amount, so its direction never has to be worked out from
            two figures. A cost line that appeared or disappeared says so instead of showing a
            misleading zero. Checks where nothing moved are left out and counted in the summary
            line: silence is information, but it is not an event.
          </p>
        </div>
      </section>

      <section class="method-section">
        <div class="method-heading">
          <p class="label method-kicker">THE LIMITS</p>
          <h2>Coverage, collection, and what is missing</h2>
        </div>
        <div class="method-prose">
          <p>
            The catalog covered here is the United States store, priced in US dollars. Pages are
            collected from authorized snapshots and approved crawl boundaries with ordinary,
            rate-limited requests; a blocked page is left blocked and reported as a gap in the
            record rather than worked around.
          </p>
          <p>
            Nothing on this site is a complete statement of Quince&rsquo;s profitability, and
            nothing on it is verified against Quince&rsquo;s books. It is an independent research
            project built from Quince&rsquo;s own published pages: if a page did not disclose a
            cost, the ledger does not know it.
          </p>
        </div>
      </section>
    </main>
  </div>
</template>
