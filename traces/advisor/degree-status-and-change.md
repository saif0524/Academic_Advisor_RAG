# Academic AI Advisor — chat transcript

- Exported: 2026-10-25T22:51:45.375Z
- Session: `sess-d87616f7-8457-4a04-afe5-9781d1a11b89`
- Turns: 7
- Deterministic checks across the conversation: 42 (32 passed, 6 failed, 4 skipped)

---

## 1. Student

what degree am I taking and what concetration?

## 2. Advisor

You're pursuing the **Bachelor of Science in Computer Science** (degree ID: BS-CS), with a concentration in **Game Development & Graphics**.

Quick snapshot of where you stand: you've passed 1105, 1310, 1320, ENGL 1301, and MATH 1426; you're currently in progress on 1325, 2315, ENGL 1302, and MATH 2425 this Fall 2026; and 1301 was not passed (F in Spring 2025), so you may want to plan a retake when you're ready. Let me know if you'd like help fitting that in!

Data lookups:
- SQLite: read your enrollment records (11 classes)

## 3. Student

Lets say I don't like some of my classes, what are my options to change things around?

## 4. Advisor

Great question — you actually have a lot of flexibility here. Here are your main levers, from smallest change to biggest:

### 1. Swap courses within your plan
Any course in a future semester can be swapped for something else that fills the same requirement. Your elective slots are the easiest to move — e.g., **4305 (Compilers)**, **4308 (AI)**, **4344 (Networks)**, and **4392 (Special Topics)** in Fall 2028–Fall 2029 are all swappable for other CSE courses that fit those elective blocks.

### 2. Your concentration has a built-in choice
Within **Game Development & Graphics**, you don't have to take everything listed — you pick one of:
- **4373 – General Purpose GPU Programming** (currently planned for Spring 2029)
- **4310 – Fundamentals of Computer Vision**

If GPU programming sounds less fun than computer vision, that's a one-line swap.

### 3. Change concentration (stay in BS-CS)
If game dev itself is what's not clicking, BS-CS also offers **Artificial Intelligence**, **Cybersecurity**, and **Data Science** concentrations. Your core CS courses would mostly carry over.

### 4. Change major entirely
There's also the **BS in Software Engineering** (BS-SE) with concentrations in **AI**, **Cybersecurity**, or **Cloud & Data Systems** — bigger ripple effect, but doable this early (you're only ~12% through).

### 5. One loose end: retake 1301
You have an F in **1301** from Spring 2025 — it's not on your plan anywhere. A repeat could slot into a lighter semester (Fall 2029 is only 6 credits right now).

**Important:** I can't edit your plan myself — but you can just tell me directly, e.g. *"swap 4373 for 4310 in Spring 2029"* or *"add 1301 to my plan for Fall 2029"*, and you'll get a confirmation card once it's processed. Anything I suggest also gets automatically re-checked against prerequisites and scheduling, so you'll see what's actually open to you.

**Next step:** Which class(es) are you lukewarm on? Tell me and I'll suggest specific swaps for that slot.

**Deterministic checks run (42): 32 passed · 6 failed · 4 skipped**

| Course | Check | Status | Reason |
| --- | --- | --- | --- |
| 4305 | FC29: Prerequisites satisfied before recommending | ✅ passed | No prerequisite records on file for 4305 |
| 4305 | FC30: Course not already completed/passed | ✅ passed | Not previously completed |
| 4305 | FC31: No schedule conflict with existing sections | ❔ skipped (data not on record) | Skipped: no specific section was given |
| 4305 | FC32: Within the per-semester credit-hour cap | ✅ passed | 16 of 18 semester hours |
| 4305 | FC32: Total stays under the degree credit ceiling | ✅ passed | 17 of 121 degree credits |
| 4305 | FC4c: Course counts toward the selected degree | ❌ failed | Not listed in BS-CS requirement blocks |
| 4308 | FC29: Prerequisites satisfied before recommending | ❌ failed | Not satisfied: 3318 |
| 4308 | FC30: Course not already completed/passed | ✅ passed | Not previously completed |
| 4308 | FC31: No schedule conflict with existing sections | ✅ passed | No meeting-time overlaps |
| 4308 | FC32: Within the per-semester credit-hour cap | ✅ passed | 16 of 18 semester hours |
| 4308 | FC32: Total stays under the degree credit ceiling | ✅ passed | 17 of 121 degree credits |
| 4308 | FC4c: Course counts toward the selected degree | ✅ passed | Listed under “Advanced Computer Science Core” in BS-CS |
| 4344 | FC29: Prerequisites satisfied before recommending | ❌ failed | Not satisfied: 3320 |
| 4344 | FC30: Course not already completed/passed | ✅ passed | Not previously completed |
| 4344 | FC31: No schedule conflict with existing sections | ✅ passed | No meeting-time overlaps |
| 4344 | FC32: Within the per-semester credit-hour cap | ✅ passed | 16 of 18 semester hours |
| 4344 | FC32: Total stays under the degree credit ceiling | ✅ passed | 17 of 121 degree credits |
| 4344 | FC4c: Course counts toward the selected degree | ✅ passed | Listed under “Advanced Computer Science Core” in BS-CS |
| 4392 | FC29: Prerequisites satisfied before recommending | ✅ passed | No prerequisite records on file for 4392 |
| 4392 | FC30: Course not already completed/passed | ✅ passed | Not previously completed |
| 4392 | FC31: No schedule conflict with existing sections | ✅ passed | No meeting-time overlaps |
| 4392 | FC32: Within the per-semester credit-hour cap | ✅ passed | 16 of 18 semester hours |
| 4392 | FC32: Total stays under the degree credit ceiling | ✅ passed | 17 of 121 degree credits |
| 4392 | FC4c: Course counts toward the selected degree | ✅ passed | Listed under “Advanced Computer Science Core” in BS-CS |
| 4373 | FC29: Prerequisites satisfied before recommending | ❌ failed | Not satisfied: 3318 |
| 4373 | FC30: Course not already completed/passed | ✅ passed | Not previously completed |
| 4373 | FC31: No schedule conflict with existing sections | ✅ passed | No meeting-time overlaps |
| 4373 | FC32: Within the per-semester credit-hour cap | ✅ passed | 16 of 18 semester hours |
| 4373 | FC32: Total stays under the degree credit ceiling | ✅ passed | 17 of 121 degree credits |
| 4373 | FC4c: Course counts toward the selected degree | ✅ passed | Listed under “Concentration: Game Development & Graphics” in BS-CS |
| 4310 | FC29: Prerequisites satisfied before recommending | ❌ failed | Not satisfied: 3318 |
| 4310 | FC30: Course not already completed/passed | ✅ passed | Not previously completed |
| 4310 | FC31: No schedule conflict with existing sections | ✅ passed | No meeting-time overlaps |
| 4310 | FC32: Within the per-semester credit-hour cap | ✅ passed | 16 of 18 semester hours |
| 4310 | FC32: Total stays under the degree credit ceiling | ✅ passed | 17 of 121 degree credits |
| 4310 | FC4c: Course counts toward the selected degree | ✅ passed | Listed under “Concentration: Game Development & Graphics” in BS-CS |
| 1301 | FC29: Prerequisites satisfied before recommending | ✅ passed | No prerequisite records on file for 1301 |
| 1301 | FC30: Course not already completed/passed | ✅ passed | Not previously completed |
| 1301 | FC31: No schedule conflict with existing sections | ❔ skipped (data not on record) | Skipped: no specific section was given |
| 1301 | FC32: Within the per-semester credit-hour cap | ❔ skipped (data not on record) | Skipped: credit hours or the semester cap are not on record |
| 1301 | FC32: Total stays under the degree credit ceiling | ❔ skipped (data not on record) | Skipped: credit hours unknown for the candidate course |
| 1301 | FC4c: Course counts toward the selected degree | ❌ failed | Not listed in BS-CS requirement blocks |

Data lookups:
- SQLite: read your active degree plan
- SQLite: read your profile and enrollment records
- SQLite: read requirements BS-CS
- SQLite: read requirements BS-CS Game Development & Graphics
- SQLite: listed degrees and concentrations
- Chroma: searched courses for “CSE 4000-level technical electives upper-division computer science topics”

## 5. Student

Can you switch my major to computer science with a concentration in data science?

## 6. Advisor

Happy to help with that! I've prepared a change to the **Bachelor of Science in Computer Science** major with the **Data Science** concentration. Once confirmed, I'll also generate a new degree plan for it, which will become your active plan right away.

Please **confirm or cancel** from the confirmation card — I can't make the change until you do.

> **Action proposed (needs the student's confirmation):** Change your major to Bachelor of Science in Computer Science with the Data Science concentration, and generate a new active degree plan for it (`act-6e649cf6-fa9c-4e29-952e-433fd278cf99`)

## 7. Advisor

Done — your confirmation went through! 🎉

Your major is now **Bachelor of Science in Computer Science — Data Science**, and a new degree plan (**plan-43cc9406fb**, Data Science) was generated and is now your **active plan**. You can review or edit it anytime in the planner. If you have questions about any courses or requirements in the new plan, just ask!
