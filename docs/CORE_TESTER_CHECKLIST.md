# Core tester checklist — 2026-11-03

Optional smoke checks for the current parser. These are existing authored development examples, not a final accuracy test. No labeling or new SMS collection is required.

Open [the tester](../tools/browser/tester.html) and refresh it. Wait for **Engine ready**. Paste each message into **SMS message**; results update as you type. Read **Message-only assessment**. The optional ownership result appears separately.

| # | Check | Message to paste | Expected main result |
| --- | --- | --- | --- | --- |
| 1 | Debit vs balance | `Available balance JOD 630.500. A completed purchase debited JOD 8.250 from account *4321.` | Include; 8.25 JOD; outgoing |
| 2 | Arabic incoming; default currency | `أُضيف 17.250 إلى حسابك.` | Include; 17.25 JOD; visible JOD default; incoming |
| 3 | Arabic digits | `خُصم ١٧٫٢٥٠ من حسابك.` | Include; 17.25 JOD; visible JOD default; outgoing |
| 4 | Person-to-person | `Outward transfer of JOD 25 completed from your account to another person, Ali.` | Include; 25 JOD; outgoing |
| 5 | Own accounts | `Transfer of JOD 45 between your own accounts completed.` | Exclude; own accounts |
| 6 | Name is not ownership proof | `Outward transfer of JOD 25 completed from account *4321 to SAMER.` | Review required; ownership unresolved |
| 7 | Authorization code | `Use code 853192 to authorize a JOD 80 purchase. Do not share the code.` | Exclude; no transaction amount |
| 8 | Declined attempt | `تم رفض عملية الشراء بقيمة ١٢ دينار لعدم كفاية الرصيد ولم يتم الخصم.` | Exclude; no transaction amount |
| 9 | Pending request | `Your payment of JOD 20 is pending approval and has not been debited.` | Exclude; no transaction amount |
| 10 | Conversational claim | `حولتلك ١٥ دينار ع المحفظة شيك عليهم بالله` | Exclude; no transaction amount |
| 11 | Stated fee-inclusive total | `17 was debited from your account; fee JOD 0.500; total debited JOD 17.500.` | Include; 17.5 JOD; outgoing |
| 12 | Account charge; visible default | `Purchase USD 10; your account was charged 7.090.` | Include; 7.09 JOD; visible JOD default; outgoing |
| 13 | Unconfirmed outcome | `Payment request for JOD 22 is closed, but whether funds were debited is not specified.` | Review required; completion uncertain |
| 14 | Conflicting postings and total | `17.250 was debited from your account and 17 was debited from your account; fee 0.500; total debited 17.500.` | Review required; amount unresolved |

For row 12, the original purchase is USD 10, but the account-charge figure is 7.090 without a unit. The existing Jordan policy uses **7.09 JOD with a visible missing-currency default**. It must not borrow USD from the original purchase. Row 11 uses the explicitly stated total; the parser must not calculate an unstated sum.

### Optional ownership and reset checks

With row 6 loaded, open **Try an ownership confirmation**. These are hypothetical test choices, not facts about SAMER: **Another person → Include**, **My own accounts → Exclude**, **I’m not sure → Review required**. The main message-only result stays Review required; inspect the separate confirmation result.

Edit the message, change Sender or the saved-contact setting, or choose **New message**: the confirmation must clear. Changing sender/contact alone must not turn conversational text into a transaction. Clear the SMS box: old amounts and ownership results must clear. If startup reports **Engine not ready**, record a startup issue; it is not a transaction exclusion.

### What a surprise means

Review required is expected when the supplied evidence cannot resolve one recordable event. A missing merchant/category must not block the core event. Text analysis does not authenticate a bank sender.

If a check differs, save the exact text, the field that differed and **Assessment response** locally so it can become a traceable regression case. Do not change the expected label just to match the output.

All 14 message examples and the three ownership choices were checked against Python, TypeScript and the actual generated tester bundle on 2026-11-03. The broader passing gate is 358 Python tests, 14 TypeScript suites and 226 frozen cases. These checks establish developer behavior, not independent real-world accuracy.

Source IDs and asserted fields are recorded in [the readiness refresh](../data/reports/behavior/core_money_r6_readiness_refresh_v1.json). See [current readiness and remaining limits](CORE_MONEY_READINESS.md).
