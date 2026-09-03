"""
Local first-aid knowledge base.

This is plain data on purpose: it runs fully offline, gives the same answer
every time for the same input, and every line in it can be reviewed and
signed off by someone qualified before it ships. That matters more here than
having something that sounds clever - a bystander mid-emergency needs
consistent, vetted steps, not generated prose.

To feed it more content: add a new dict to TOPICS following the same shape.
`keywords` drives matching against the incident description / free-text
questions. `types` restricts which incident types will surface this topic
by default.

None of this replaces professional medical care or the responders already
being dispatched - every topic carries that reminder through to the UI.
"""

TOPICS = [
    {
        "id": "severe_bleeding",
        "title": "Severe bleeding",
        "types": ["road_accident", "security", "other"],
        "keywords": ["bleeding", "blood", "cut", "wound", "gash", "stab", "laceration", "hemorrhage"],
        "steps": [
            "Call out for the emergency line to stay on hold - responders are already on the way.",
            "Apply firm, direct pressure to the wound with a clean cloth or your hand.",
            "Do not remove any object stuck in the wound - pack material around it instead and keep pressing.",
            "If bleeding soaks through, add more material on top rather than lifting the first layer to check.",
            "Keep the injured area raised above heart level if possible, without moving the person more than necessary.",
            "If the person becomes pale, cold, or confused, lay them flat and raise their legs slightly - signs of shock.",
        ],
        "warnings": ["Do not apply a tourniquet unless bleeding is life-threatening and you've been trained to use one."],
    },
    {
        "id": "entrapment",
        "title": "Someone is trapped",
        "types": ["road_accident"],
        "keywords": ["trapped", "entrapment", "stuck", "pinned", "wreckage", "crushed"],
        "steps": [
            "Do not try to free a trapped person by force - further injury is common.",
            "If there's no fire or fuel leak risk, stay with them and keep them calm and still.",
            "Turn off the vehicle's ignition if you can safely reach it, to reduce fire risk.",
            "Keep them talking - track responsiveness so you can report any change when responders arrive.",
            "If you smell fuel or see smoke, move a safe distance away and warn others - do not attempt extraction yourself.",
        ],
        "warnings": ["Never move a trapped person with a suspected spinal injury unless there is an immediate life threat (e.g. fire)."],
    },
    {
        "id": "unconscious_breathing",
        "title": "Unconscious but breathing",
        "types": ["road_accident", "medical", "other"],
        "keywords": ["unconscious", "unresponsive", "passed out", "fainted", "not waking up"],
        "steps": [
            "Check they are breathing normally - watch the chest rise and fall for 10 seconds.",
            "If breathing, gently roll them onto their side into the recovery position (top leg bent, head tilted back slightly to keep the airway open).",
            "Loosen anything tight around the neck.",
            "Keep monitoring their breathing until responders arrive - be ready to report if it stops.",
            "Do not give them anything to eat or drink.",
        ],
        "warnings": ["If they stop breathing normally at any point, begin CPR - see the 'not breathing' guidance."],
    },
    {
        "id": "cpr",
        "title": "Not breathing / no pulse",
        "types": ["medical", "road_accident"],
        "keywords": ["not breathing", "no pulse", "cardiac arrest", "heart stopped", "collapsed", "cpr"],
        "steps": [
            "Confirm unresponsiveness - tap their shoulders and shout. If no response and no normal breathing, start CPR immediately.",
            "Place the heel of one hand on the center of the chest, other hand on top, fingers interlaced.",
            "Push hard and fast, straight down, about 5cm deep, at a steady rate (roughly 100-120 pushes per minute - similar tempo to a fast heartbeat).",
            "Let the chest fully rise between compressions.",
            "Continue compressions without stopping until responders take over or the person starts breathing normally.",
            "If you're not trained in rescue breaths, hands-only compressions are still effective - don't stop to attempt breaths if unsure.",
        ],
        "warnings": ["This is general bystander guidance, not a substitute for CPR training. Compressions on someone who is breathing normally can cause harm - confirm breathing first."],
    },
    {
        "id": "choking",
        "title": "Choking",
        "types": ["medical", "other"],
        "keywords": ["choking", "can't breathe", "swallowed", "airway blocked", "gagging"],
        "steps": [
            "If they can cough or speak, encourage them to keep coughing - don't intervene yet.",
            "If they cannot breathe, speak, or cough: stand behind them, lean them forward, and give up to 5 sharp blows between the shoulder blades with the heel of your hand.",
            "If that doesn't clear it, give up to 5 abdominal thrusts: stand behind them, fist above the navel, grasp with your other hand, and pull sharply inward and upward.",
            "Alternate 5 back blows and 5 abdominal thrusts until the object clears or they become unresponsive.",
            "If they become unresponsive, lower them to the ground carefully and begin CPR.",
        ],
        "warnings": ["Do not do abdominal thrusts on infants under 1 year or visibly pregnant people - use back blows and chest thrusts instead if trained."],
    },
    {
        "id": "burns",
        "title": "Burns",
        "types": ["fire", "other"],
        "keywords": ["burn", "burned", "burnt", "scald", "fire injury"],
        "steps": [
            "Move the person away from the heat source once it's safe to do so.",
            "Cool the burn under cool (not ice-cold) running water for 20 minutes.",
            "Remove nearby clothing and jewellery before swelling starts, unless it's stuck to the burn.",
            "Cover loosely with cling film or a clean, non-fluffy cloth - don't wrap tightly.",
            "Do not apply ice, butter, oil, or toothpaste to the burn.",
            "Do not burst any blisters.",
        ],
        "warnings": ["Treat any burn as urgent if it's larger than the person's palm, on the face/hands/genitals, or the person is a child."],
    },
    {
        "id": "smoke_inhalation",
        "title": "Smoke inhalation",
        "types": ["fire"],
        "keywords": ["smoke", "inhaled smoke", "coughing", "can't see", "toxic fumes"],
        "steps": [
            "Get the person into fresh air immediately if it's safe for you to help them move.",
            "Loosen tight clothing around the neck and chest.",
            "Keep them sitting upright if conscious - it's usually easier to breathe than lying flat.",
            "Watch for worsening coughing, wheezing, or confusion and be ready to report it.",
            "Do not re-enter a smoke-filled area to retrieve belongings.",
        ],
        "warnings": [],
    },
    {
        "id": "seizure",
        "title": "Seizure / convulsions",
        "types": ["medical"],
        "keywords": ["seizure", "convulsing", "fitting", "epileptic", "shaking uncontrollably"],
        "steps": [
            "Clear the area of anything they could hit themselves on.",
            "Do not hold them down or restrain their movements.",
            "Do not put anything in their mouth.",
            "Cushion their head if possible with something soft.",
            "Time the seizure if you can - this matters for responders.",
            "Once the shaking stops, roll them into the recovery position and stay with them until they're fully alert.",
        ],
        "warnings": ["Treat as urgent if the seizure lasts more than 5 minutes, repeats without recovery in between, or they don't regain consciousness."],
    },
    {
        "id": "chest_pain",
        "title": "Chest pain / suspected heart attack",
        "types": ["medical"],
        "keywords": ["chest pain", "heart attack", "tight chest", "arm pain", "crushing pain"],
        "steps": [
            "Help them into a comfortable, resting position - usually sitting, slightly leaning back, knees bent.",
            "Keep them calm and still - do not let them walk around or exert themselves.",
            "Loosen tight clothing.",
            "If they carry prescribed heart medication (e.g. their own aspirin or GTN spray), they can take it themselves as prescribed - don't give them anything not prescribed to them.",
            "Monitor breathing and responsiveness closely and be ready to start CPR if they become unresponsive and stop breathing normally.",
        ],
        "warnings": [],
    },
    {
        "id": "shock",
        "title": "Shock (pale, cold, rapid breathing)",
        "types": ["road_accident", "medical", "fire", "security", "other"],
        "keywords": ["shock", "pale", "clammy", "dizzy", "faint", "rapid breathing"],
        "steps": [
            "Lay the person down and raise their legs about 30cm if there's no suspected leg or spinal injury.",
            "Keep them warm with a blanket or clothing, but don't overheat them.",
            "Loosen tight clothing.",
            "Keep talking to them calmly - reassurance genuinely helps.",
            "Do not give them food or drink.",
        ],
        "warnings": [],
    },
    {
        "id": "allergic_reaction",
        "title": "Severe allergic reaction",
        "types": ["medical"],
        "keywords": ["allergic", "allergy", "anaphylaxis", "swelling face", "hives", "throat closing"],
        "steps": [
            "If they carry their own epinephrine auto-injector, help them use it as prescribed to them.",
            "Help them into a comfortable position - lying down with legs raised if they feel faint, or sitting up if breathing is difficult.",
            "Loosen tight clothing.",
            "Watch closely for worsening swelling or breathing difficulty.",
            "Begin CPR if they become unresponsive and stop breathing normally.",
        ],
        "warnings": ["A second reaction can occur even after symptoms improve - they still need to be seen by responders."],
    },
]


def all_topics():
    return TOPICS
