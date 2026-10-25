# Academic AI Advisor — chat transcript

- Exported: 2026-10-25T22:53:53.795Z
- Session: `sess-20aa6f6d-b14b-4397-b3f0-1554cdb9718f`
- Turns: 4
- Deterministic checks across the conversation: 6 (4 passed, 2 failed, 0 skipped)

---

## 1. Student

What are classes I don't meet pre-requisites for? Give me a flat list

## 2. Advisor

I don't have that list — the audit I ran covers degree progress only, and it didn't include any per-course prerequisite checks, so there are no prerequisite results to report (no passes or failures came back).

What the audit does show is your standing in BS-CS: 11.6% complete, 14 hours earned, with big blocks still open like Advanced CS Core (23 hrs), Life & Physical Sciences (12 hrs), and your Data Science concentration (9 hrs).

If you want prerequisite answers, just name specific courses — for example ones from your plan like 4303 (Computer Graphics), 4308 (AI), or 4309 (Fundamentals of Machine Learning) — and I can run a prerequisite check on each and give you that flat list.

## 3. Student

4303 (Computer Graphics)

## 4. Advisor

Here's the audit for **4303 – Computer Graphics** (3 credit hours): unfortunately, it's **not eligible** right now, for two reasons:

- **Prerequisites (FC29): Not satisfied** — it requires 3318, which you haven't completed yet.
- **Degree fit (FC4c): Not listed** in the BS-CS requirement blocks, so it wouldn't count toward your selected degree.

The good news: you haven't taken it before (FC30 ✓), there are no schedule conflicts (FC31 ✓), and adding it would stay within your limits — 16 of 18 semester hours for the term and 17 of 121 degree credits (FC32 ✓).

If you're still interested, your best path is to complete 3318 first — but since 4303 doesn't count toward the BS-CS degree, you may want to check whether it would fit better as an elective under a different plan. Want me to look up 3318 or suggest courses that do count toward your requirements?

**Deterministic checks run (6): 4 passed · 2 failed · 0 skipped**

| Course | Check | Status | Reason |
| --- | --- | --- | --- |
| 4303 | FC29: Prerequisites satisfied before recommending | ❌ failed | Not satisfied: 3318 |
| 4303 | FC30: Course not already completed/passed | ✅ passed | Not previously completed |
| 4303 | FC31: No schedule conflict with existing sections | ✅ passed | No meeting-time overlaps |
| 4303 | FC32: Within the per-semester credit-hour cap | ✅ passed | 16 of 18 semester hours |
| 4303 | FC32: Total stays under the degree credit ceiling | ✅ passed | 17 of 121 degree credits |
| 4303 | FC4c: Course counts toward the selected degree | ❌ failed | Not listed in BS-CS requirement blocks |
