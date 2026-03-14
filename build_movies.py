#!/usr/bin/env python3
"""Generate movies.json with 500 movies in the required format."""
import json
import re

# Movies: list of (title, year, genres[], moods[], language)
# Corpora list first (title (year) format parsed), then additional films
CORPORA_RAW = """
The Godfather (1972)|Drama,Crime|intense,emotional|English
Schindler's List (1993)|Drama,History,War|emotional,powerful|English
Raging Bull (1980)|Drama,Sport,Biography|intense,raw|English
Casablanca (1942)|Romance,Drama,War|romantic,classic|English
Citizen Kane (1941)|Drama,Mystery|cinematic,complex|English
Gone with the Wind (1939)|Romance,Drama,War|epic,romantic|English
The Wizard of Oz (1939)|Fantasy,Adventure,Family|whimsical,nostalgic|English
One Flew Over the Cuckoo's Nest (1975)|Drama|rebellious,emotional|English
Lawrence of Arabia (1962)|Adventure,Drama,War|epic,cinematic|English
Vertigo (1958)|Thriller,Mystery,Romance|suspenseful,stylish|English
Psycho (1960)|Horror,Thriller,Mystery|suspenseful,tense|English
The Godfather: Part II (1974)|Drama,Crime|intense,epic|English
On the Waterfront (1954)|Drama,Crime|gritty,emotional|English
Forrest Gump (1994)|Drama,Romance|heartwarming,nostalgic|English
The Sound of Music (1965)|Musical,Family,Drama|uplifting,romantic|English
12 Angry Men (1957)|Drama|tense,thought-provoking|English
West Side Story (1961)|Musical,Romance,Drama|romantic,stylish|English
Star Wars: Episode IV - A New Hope (1977)|Sci-Fi,Adventure,Action|adventurous,epic|English
2001: A Space Odyssey (1968)|Sci-Fi,Adventure,Mystery|contemplative,visually stunning|English
Chinatown (1974)|Drama,Mystery,Thriller|noir,complex|English
Singin' in the Rain (1952)|Musical,Comedy,Romance|joyful,stylish|English
It's a Wonderful Life (1946)|Drama,Family,Fantasy|heartwarming,uplifting|English
Dr. Strangelove or: How I Learned to Stop Worrying and Love the Bomb (1964)|Comedy,War,Satire|dark humor,witty|English
Some Like It Hot (1959)|Comedy,Romance|witty,fun|English
Ben-Hur (1959)|Adventure,Drama,History|epic,spectacular|English
Apocalypse Now (1979)|Drama,War|intense,visceral|English
The Lord of the Rings: The Return of the King (2003)|Fantasy,Adventure,Drama|epic,emotional|English
Gladiator (2000)|Action,Drama,Adventure|epic,intense|English
Unforgiven (1992)|Western,Drama|gritty,contemplative|English
Raiders of the Lost Ark (1981)|Adventure,Action|adventurous,fun|English
Rocky (1976)|Drama,Sport|inspirational,uplifting|English
A Streetcar Named Desire (1951)|Drama|intense,emotional|English
To Kill a Mockingbird (1962)|Drama|thought-provoking,emotional|English
My Fair Lady (1964)|Musical,Romance,Comedy|charming,stylish|English
A Clockwork Orange (1971)|Sci-Fi,Drama,Crime|disturbing,stylish|English
Doctor Zhivago (1965)|Drama,Romance,War|romantic,epic|English
The Searchers (1956)|Western,Adventure,Drama|cinematic,contemplative|English
Jaws (1975)|Thriller,Adventure,Horror|tense,thrilling|English
Patton (1970)|Drama,War,Biography|epic,intense|English
Butch Cassidy and the Sundance Kid (1969)|Western,Comedy,Adventure|charming,adventurous|English
The Good, the Bad and the Ugly (1966)|Western,Adventure|stylish,epic|Italian
The Apartment (1960)|Comedy,Drama,Romance|witty,romantic|English
Platoon (1986)|Drama,War|intense,visceral|English
Braveheart (1995)|Drama,War,History|epic,inspiring|English
Dances with Wolves (1990)|Western,Drama,Adventure|contemplative,epic|English
The Exorcist (1973)|Horror,Drama|disturbing,tense|English
The Pianist (2002)|Drama,War,Biography|emotional,powerful|English
Goodfellas (1990)|Drama,Crime|intense,stylish|English
The Deer Hunter (1978)|Drama,War|emotional,intense|English
All Quiet on the Western Front (1930)|Drama,War|grim,powerful|English
Bonnie and Clyde (1967)|Drama,Crime,Biography|stylish,violent|English
The French Connection (1971)|Action,Crime,Thriller|gritty,tense|English
Midnight Cowboy (1969)|Drama|gritty,emotional|English
Mr. Smith Goes to Washington (1939)|Drama,Comedy|inspirational,heartwarming|English
Rain Man (1988)|Drama|emotional,touching|English
Annie Hall (1977)|Comedy,Romance,Drama|witty,romantic|English
Fargo (1996)|Crime,Drama,Thriller|dark humor,tense|English
Close Encounters of the Third Kind (1977)|Sci-Fi,Drama|wonder,contemplative|English
Nashville (1975)|Drama,Comedy,Music|satirical,complex|English
Network (1976)|Drama,Satire|sharp,satirical|English
The Graduate (1967)|Comedy,Drama,Romance|witty,romantic|English
American Graffiti (1973)|Comedy,Drama|nostalgic,fun|English
Pulp Fiction (1994)|Crime,Thriller,Drama|stylish,violent|English
Terms of Endearment (1983)|Drama,Comedy|emotional,heartwarming|English
The Great Dictator (1940)|Comedy,Drama,War|satirical,emotional|English
Double Indemnity (1944)|Crime,Drama,Mystery|noir,suspenseful|English
The Maltese Falcon (1941)|Crime,Drama,Mystery|noir,stylish|English
Taxi Driver (1976)|Drama,Thriller|dark,intense|English
Rear Window (1954)|Thriller,Mystery,Romance|suspenseful,stylish|English
The Third Man (1949)|Thriller,Mystery,Drama|noir,atmospheric|English
Rebel Without a Cause (1955)|Drama|rebellious,emotional|English
North by Northwest (1959)|Thriller,Adventure,Romance|suspenseful,stylish|English
Tom Jones (1963)|Comedy,Adventure,Romance|witty,romantic|English
A Man for All Seasons (1966)|Drama,History|thought-provoking,stirring|English
In the Heat of the Night (1967)|Drama,Thriller,Crime|tense,powerful|English
Oliver! (1968)|Musical,Drama,Family|charming,uplifting|English
The Sting (1973)|Comedy,Crime,Drama|clever,fun|English
Kramer vs. Kramer (1979)|Drama|emotional,touching|English
Ordinary People (1980)|Drama|emotional,raw|English
Chariots of Fire (1981)|Drama,Sport,History|inspiring,emotional|English
Gandhi (1982)|Drama,Biography,History|epic,inspiring|English
Out of Africa (1985)|Drama,Romance|romantic,epic|English
The Last Emperor (1987)|Drama,History,Biography|epic,visually stunning|English
Driving Miss Daisy (1989)|Drama,Comedy|heartwarming,touching|English
The English Patient (1996)|Drama,Romance,War|romantic,emotional|English
Shakespeare in Love (1998)|Comedy,Romance,Drama|charming,witty|English
American Beauty (1999)|Drama|dark,satirical|English
A Beautiful Mind (2001)|Drama,Biography,Romance|emotional,inspiring|English
Chicago (2002)|Musical,Crime,Drama|stylish,glamorous|English
Million Dollar Baby (2004)|Drama,Sport|emotional,powerful|English
Crash (2005)|Drama,Crime|thought-provoking,intense|English
The Departed (2006)|Crime,Drama,Thriller|tense,intense|English
No Country for Old Men (2007)|Crime,Drama,Thriller|tense,bleak|English
Slumdog Millionaire (2008)|Drama,Romance|uplifting,emotional|English
The Hurt Locker (2009)|Drama,War,Thriller|tense,intense|English
The King's Speech (2010)|Drama,Biography,History|inspiring,emotional|English
The Artist (2011)|Comedy,Drama,Romance|charming,nostalgic|French
Argo (2012)|Drama,Thriller,History|tense,thrilling|English
12 Years a Slave (2013)|Drama,History|powerful,emotional|English
Birdman (2014)|Comedy,Drama|stylish,witty|English
Spotlight (2015)|Drama,History,Thriller|tense,thought-provoking|English
Moonlight (2016)|Drama|emotional,poetic|English
The Shape of Water (2017)|Drama,Fantasy,Romance|romantic,whimsical|English
Black Swan (2010)|Drama,Thriller,Horror|intense,psychological|English
Inception (2010)|Sci-Fi,Action,Thriller|mind-bending,visually stunning|English
The Social Network (2010)|Drama,Biography|sharp,witty|English
Toy Story 3 (2010)|Animation,Adventure,Comedy|emotional,heartwarming|English
True Grit (2010)|Western,Drama,Adventure|gritty,atmospheric|English
Moneyball (2011)|Drama,Sport,Biography|smart,inspiring|English
War Horse (2011)|Drama,War,Adventure|emotional,epic|English
Life of Pi (2012)|Adventure,Drama,Fantasy|visually stunning,contemplative|English
Silver Linings Playbook (2012)|Comedy,Drama,Romance|charming,emotional|English
Zero Dark Thirty (2012)|Drama,Thriller,History|tense,grim|English
Dallas Buyers Club (2013)|Drama,Biography|emotional,inspiring|English
Gravity (2013)|Sci-Fi,Drama,Thriller|tense,visually stunning|English
Her (2013)|Drama,Romance,Sci-Fi|thought-provoking,romantic|English
The Wolf of Wall Street (2013)|Comedy,Crime,Drama|excessive,dark humor|English
American Sniper (2014)|Drama,War,Biography|intense,emotional|English
Boyhood (2014)|Drama|naturalistic,emotional|English
The Grand Budapest Hotel (2014)|Comedy,Drama|whimsical,stylish|English
The Imitation Game (2014)|Drama,Biography,Thriller|tense,inspiring|English
Selma (2014)|Drama,History,Biography|powerful,inspiring|English
Whiplash (2014)|Drama,Music|intense,thrilling|English
The Big Short (2015)|Comedy,Drama,Biography|sharp,witty|English
Mad Max: Fury Road (2015)|Action,Sci-Fi,Adventure|intense,visually stunning|English
The Martian (2015)|Sci-Fi,Adventure,Drama|inspiring,witty|English
The Revenant (2015)|Drama,Adventure,Western|visceral,visually stunning|English
Arrival (2016)|Sci-Fi,Drama,Mystery|thought-provoking,emotional|English
Hidden Figures (2016)|Drama,History,Biography|inspiring,heartwarming|English
La La Land (2016)|Romance,Drama,Musical|emotional,stylish|English
Manchester by the Sea (2016)|Drama|emotional,raw|English
Call Me by Your Name (2017)|Drama,Romance|romantic,lyrical|English
Dunkirk (2017)|Drama,War,Thriller|tense,immersive|English
Get Out (2017)|Horror,Thriller,Mystery|tense,satirical|English
Lady Bird (2017)|Comedy,Drama|warm,witty|English
Phantom Thread (2017)|Drama,Romance|stylish,complex|English
The Post (2017)|Drama,History,Thriller|tense,inspiring|English
Three Billboards Outside Ebbing Missouri (2017)|Drama,Crime,Comedy|dark humor,emotional|English
Chocolat (2000)|Romance,Drama,Comedy|charming,whimsical|English
Crouching Tiger Hidden Dragon (2000)|Action,Drama,Romance|stylish,poetic|Mandarin
Erin Brockovich (2000)|Drama,Biography|inspiring,feisty|English
Traffic (2000)|Drama,Crime,Thriller|complex,gritty|English
The Lord of the Rings: The Fellowship of the Ring (2001)|Fantasy,Adventure,Drama|epic,immersive|English
Moulin Rouge! (2001)|Musical,Romance,Drama|glamorous,romantic|English
Gangs of New York (2002)|Drama,Crime,History|gritty,epic|English
The Hours (2002)|Drama|emotional,literary|English
The Lord of the Rings: The Two Towers (2002)|Fantasy,Adventure,Drama|epic,thrilling|English
Lost in Translation (2003)|Drama,Romance|melancholic,stylish|English
Master and Commander: The Far Side of the World (2003)|Adventure,Drama,War|epic,immersive|English
Mystic River (2003)|Drama,Crime,Thriller|dark,emotional|English
Seabiscuit (2003)|Drama,Sport,History|inspiring,emotional|English
Sideways (2004)|Comedy,Drama|witty,contemplative|English
Brokeback Mountain (2005)|Drama,Romance|romantic,tragic|English
Capote (2005)|Drama,Biography,Crime|contemplative,complex|English
Good Night and Good Luck (2005)|Drama,History,Biography|sharp,tense|English
Little Miss Sunshine (2006)|Comedy,Drama|heartwarming,dark humor|English
Juno (2007)|Comedy,Drama,Romance|witty,charming|English
There Will Be Blood (2007)|Drama|intense,epic|English
The Curious Case of Benjamin Button (2008)|Drama,Romance,Fantasy|romantic,contemplative|English
Avatar (2009)|Sci-Fi,Adventure,Action|visually stunning,epic|English
District 9 (2009)|Sci-Fi,Thriller,Drama|gritty,thought-provoking|English
Inglourious Basterds (2009)|Adventure,Drama,War|stylish,dark humor|English
Up (2009)|Animation,Adventure,Comedy|emotional,heartwarming|English
Blade Runner (1982)|Sci-Fi,Thriller,Drama|noir,atmospheric|English
Beetlejuice (1988)|Comedy,Fantasy,Horror|quirky,fun|English
Ghostbusters (1984)|Comedy,Fantasy,Sci-Fi|fun,nostalgic|English
Back to the Future (1985)|Sci-Fi,Adventure,Comedy|fun,clever|English
The Princess Bride (1987)|Adventure,Comedy,Family|charming,witty|English
The Goonies (1985)|Adventure,Comedy,Family|fun,adventurous|English
The Shining (1980)|Horror,Drama,Thriller|terrifying,atmospheric|English
Full Metal Jacket (1987)|Drama,War|grim,intense|English
Top Gun (1986)|Action,Drama|stylish,thrilling|English
The Outsiders (1983)|Drama|emotional,rebellious|English
Uncle Buck (1989)|Comedy,Family|heartwarming,fun|English
The Karate Kid (1984)|Drama,Sport,Family|inspiring,heartwarming|English
E.T. the Extra-Terrestrial (1982)|Sci-Fi,Family,Drama|heartwarming,wonder|English
The Breakfast Club (1985)|Comedy,Drama|nostalgic,witty|English
Dune (1984)|Sci-Fi,Adventure|epic,atmospheric|English
Aliens (1986)|Sci-Fi,Action,Horror|tense,thrilling|English
Stand by Me (1986)|Adventure,Drama|nostalgic,emotional|English
Scarface (1983)|Crime,Drama|violent,intense|English
Road House (1989)|Action,Drama|cheesy,fun|English
Die Hard (1988)|Action,Thriller|thrilling,fun|English
Dirty Dancing (1987)|Drama,Romance,Music|romantic,nostalgic|English
Batman (1989)|Action,Crime,Fantasy|dark,stylish|English
Star Wars: Episode VI - Return of the Jedi (1983)|Sci-Fi,Adventure,Action|adventurous,fun|English
Star Wars: Episode V - The Empire Strikes Back (1980)|Sci-Fi,Adventure,Action|epic,thrilling|English
Ferris Bueller's Day Off (1986)|Comedy|fun,witty|English
Predator (1987)|Action,Sci-Fi,Thriller|tense,thrilling|English
The Little Mermaid (1989)|Animation,Family,Musical|charming,romantic|English
Dead Poets Society (1989)|Drama|inspiring,emotional|English
The Thing (1982)|Horror,Sci-Fi,Mystery|tense,paranoid|English
Heathers (1988)|Comedy,Drama|dark,witty|English
The Terminator (1984)|Sci-Fi,Action,Thriller|tense,thrilling|English
Ghostbusters II (1989)|Comedy,Fantasy,Sci-Fi|fun,nostalgic|English
Once Upon a Time in America (1984)|Crime,Drama|epic,noir|English
Coming to America (1988)|Comedy,Romance|fun,charming|English
Indiana Jones and the Last Crusade (1989)|Adventure,Action|adventurous,fun|English
Airplane! (1980)|Comedy|silly,witty|English
Fast Times at Ridgemont High (1982)|Comedy,Drama|nostalgic,fun|English
Indiana Jones and the Temple of Doom (1984)|Adventure,Action|adventurous,thrilling|English
TRON (1982)|Sci-Fi,Action,Adventure|visually striking,nostalgic|English
Caddyshack (1980)|Comedy,Sport|silly,fun|English
Beverly Hills Cop (1984)|Comedy,Action,Crime|fun,witty|English
The Evil Dead (1981)|Horror,Comedy|campy,scary|English
Highlander (1986)|Action,Fantasy,Adventure|cheesy,epic|English
The NeverEnding Story (1984)|Fantasy,Adventure,Family|whimsical,nostalgic|English
The Shawshank Redemption (1994)|Drama|hopeful,emotional|English
Jumanji (1995)|Adventure,Family,Fantasy|fun,adventurous|English
The Silence of the Lambs (1991)|Thriller,Crime,Drama|tense,psychological|English
The Lion King (1994)|Animation,Adventure,Family|emotional,epic|English
Titanic (1997)|Drama,Romance,Disaster|romantic,epic|English
Eyes Wide Shut (1999)|Drama,Mystery,Thriller|dreamlike,erotic|English
The Professional (1994)|Action,Crime,Drama|stylish,emotional|English
The Matrix (1999)|Sci-Fi,Action|mind-bending,stylish|English
Deep Impact (1998)|Sci-Fi,Drama,Thriller|tense,emotional|English
Casino (1995)|Crime,Drama|epic,intense|English
The Green Mile (1999)|Drama,Fantasy,Crime|emotional,powerful|English
Fight Club (1999)|Drama,Thriller|subversive,intense|English
Jurassic Park (1993)|Adventure,Sci-Fi,Thriller|thrilling,wonder|English
Saving Private Ryan (1998)|Drama,War|intense,visceral|English
The Fifth Element (1997)|Sci-Fi,Action,Adventure|stylish,fun|English
The Big Lebowski (1998)|Comedy,Crime|quirky,witty|English
American Pie (1999)|Comedy|raunchy,fun|English
Beauty and the Beast (1991)|Animation,Family,Musical|romantic,charming|English
Se7en (1995)|Crime,Thriller,Mystery|dark,tense|English
10 Things I Hate About You (1999)|Comedy,Romance|witty,charming|English
Toy Story (1995)|Animation,Adventure,Comedy|heartwarming,fun|English
Boogie Nights (1997)|Drama|excessive,stylish|English
Cruel Intentions (1999)|Drama,Romance,Thriller|stylish,dark|English
Romeo + Juliet (1996)|Romance,Drama|stylish,romantic|English
The Usual Suspects (1995)|Crime,Mystery,Thriller|clever,tense|English
Good Will Hunting (1997)|Drama,Romance|emotional,inspiring|English
Heat (1995)|Crime,Drama,Thriller|tense,epic|English
Star Wars: Episode I - The Phantom Menace (1999)|Sci-Fi,Adventure,Action|epic,visually stunning|English
American History X (1998)|Drama|intense,powerful|English
The Mummy (1999)|Adventure,Action,Fantasy|fun,adventurous|English
Clueless (1995)|Comedy,Romance|witty,charming|English
Reservoir Dogs (1992)|Crime,Thriller|stylish,violent|English
Basic Instinct (1992)|Thriller,Mystery,Erotic|suspenseful,steamy|English
Magnolia (1999)|Drama|complex,emotional|English
The Sixth Sense (1999)|Drama,Thriller,Mystery|eerie,emotional|English
The Truman Show (1998)|Comedy,Drama,Sci-Fi|thought-provoking,charming|English
Waterworld (1995)|Sci-Fi,Adventure,Action|epic,adventurous|English
Terminator 2: Judgment Day (1991)|Sci-Fi,Action,Thriller|thrilling,emotional|English
Trainspotting (1996)|Drama,Comedy|gritty,dark humor|English
Dazed and Confused (1993)|Comedy,Drama|nostalgic,laid-back|English
Pretty Woman (1990)|Comedy,Romance|charming,romantic|English
"""

def parse_line(line):
    parts = line.strip().split("|")
    if len(parts) < 4:
        return None
    title = parts[0].strip()
    year_match = re.search(r"\((\d{4})\)\s*$", title)
    if year_match:
        year = int(year_match.group(1))
        title = re.sub(r"\s*\(\d{4}\)\s*$", "", title).strip()
    else:
        year = 2000  # fallback
    genres = [g.strip() for g in parts[1].split(",")]
    moods = [m.strip() for m in parts[2].split(",")]
    language = parts[3].strip()
    return {"title": title, "year": year, "genre": genres, "mood": moods, "language": language}

# Additional movies to reach 500 (title|year|genre|mood|language)
EXTRA_MOVIES = """
Amélie (2001)|Romance,Comedy,Drama|whimsical,charming|French
Pan's Labyrinth (2006)|Fantasy,Drama,War|dark,whimsical|Spanish
Parasite (2019)|Drama,Thriller,Comedy|satirical,tense|Korean
Spirited Away (2001)|Animation,Fantasy,Adventure|magical,whimsical|Japanese
Cidade de Deus (2002)|Crime,Drama|gritty,visceral|Portuguese
Oldboy (2003)|Thriller,Drama,Mystery|intense,disturbing|Korean
The Lives of Others (2006)|Drama,Thriller|tense,emotional|German
Cinema Paradiso (1988)|Drama,Romance|nostalgic,emotional|Italian
Life Is Beautiful (1997)|Comedy,Drama,War|heartwarming,emotional|Italian
Amadeus (1984)|Drama,Biography,Music|opulent,inspiring|English
The Blue Lagoon (1980)|Adventure,Romance,Drama|romantic,exotic|English
Weekend at Bernie's (1989)|Comedy|silly,fun|English
Newsies (1992)|Musical,Family,Drama|uplifting,nostalgic|English
Darkest Hour (2017)|Drama,War,Biography|tense,inspiring|English
Birdman or (The Unexpected Virtue of Ignorance) (2014)|Comedy,Drama|stylish,witty|English
One Flew Over The Cuckoo's Nest (1975)|Drama|rebellious,emotional|English
Crouching Tiger Hidden Dragon (2000)|Action,Drama,Romance|stylish,poetic|Mandarin
Good Night and Good Luck (2005)|Drama,History,Biography|sharp,tense|English
Three Billboards Outside Ebbing Missouri (2017)|Drama,Crime,Comedy|dark humor,emotional|English
The Intouchables (2011)|Comedy,Drama|heartwarming,uplifting|French
A Separation (2011)|Drama,Mystery|tense,emotional|Persian
Roma (2018)|Drama|contemplative,emotional|Spanish
Rashomon (1950)|Drama,Mystery,Crime|complex,philosophical|Japanese
Seven Samurai (1954)|Drama,Action,Adventure|epic,action-packed|Japanese
Yojimbo (1961)|Action,Drama|stylish,witty|Japanese
Run Lola Run (1998)|Thriller,Crime,Romance|energetic,stylish|German
Downfall (2004)|Drama,War,History|grim,powerful|German
The White Ribbon (2009)|Drama,Mystery|unsettling,atmospheric|German
Das Boot (1981)|Drama,War,Thriller|claustrophobic,tense|German
Metropolis (1927)|Sci-Fi,Drama|visually stunning,epic|German
Nosferatu (1922)|Horror,Fantasy|atmospheric,creepy|German
M (1931)|Thriller,Crime,Drama|tense,noir|German
Wings of Desire (1987)|Drama,Fantasy,Romance|poetic,contemplative|German
The Tin Drum (1979)|Drama,War,Fantasy|surreal,disturbing|German
The Bicycle Thieves (1948)|Drama|emotional,realistic|Italian
La Dolce Vita (1960)|Drama,Comedy|stylish,satirical|Italian
8½ (1963)|Drama,Fantasy|surreal,stylish|Italian
Bicycle Thieves (1948)|Drama|emotional,realistic|Italian
The Conformist (1970)|Drama,Thriller|stylish,complex|Italian
Il Postino (1994)|Comedy,Drama,Romance|charming,romantic|Italian
Malena (2000)|Drama,Romance,War|romantic,nostalgic|Italian
Cinema Paradiso (1988)|Drama,Romance|nostalgic,emotional|Italian
The 400 Blows (1959)|Drama|emotional,raw|French
Breathless (1960)|Drama,Crime,Romance|stylish,rebellious|French
Jules and Jim (1962)|Drama,Romance|romantic,complex|French
The Umbrellas of Cherbourg (1964)|Musical,Romance,Drama|romantic,colorful|French
A Man and a Woman (1966)|Drama,Romance|romantic,stylish|French
The Discreet Charm of the Bourgeoisie (1972)|Comedy,Drama,Fantasy|surreal,satirical|French
Jean de Florette (1986)|Drama|emotional,lyrical|French
Manon of the Spring (1986)|Drama|emotional,tragic|French
Cyrano de Bergerac (1990)|Drama,Romance,Comedy|romantic,witty|French
The Diving Bell and the Butterfly (2007)|Drama,Biography|emotional,poetic|French
Tell No One (2006)|Thriller,Drama,Mystery|tense,clever|French
Incendies (2010)|Drama,Mystery,War|powerful,emotional|French
Rust and Bone (2012)|Drama,Romance|raw,emotional|French
Blue Is the Warmest Color (2013)|Drama,Romance|emotional,raw|French
Portrait of a Lady on Fire (2019)|Drama,Romance|romantic,lyrical|French
Memories of Murder (2003)|Crime,Drama,Thriller|tense,atmospheric|Korean
The Host (2006)|Horror,Sci-Fi,Thriller|thrilling,emotional|Korean
Burning (2018)|Drama,Mystery,Thriller|slow-burn,tense|Korean
Train to Busan (2016)|Action,Horror,Drama|tense,emotional|Korean
The Handmaiden (2016)|Drama,Thriller,Romance|stylish,erotic|Korean
Snowpiercer (2013)|Sci-Fi,Action,Drama|dystopian,intense|English
Okja (2017)|Adventure,Drama,Sci-Fi|emotional,quirky|English
My Neighbor Totoro (1988)|Animation,Fantasy,Family|whimsical,heartwarming|Japanese
Princess Mononoke (1997)|Animation,Adventure,Fantasy|epic,environmental|Japanese
Howl's Moving Castle (2004)|Animation,Adventure,Fantasy|whimsical,romantic|Japanese
Grave of the Fireflies (1988)|Animation,Drama,War|devastating,emotional|Japanese
Akira (1988)|Animation,Sci-Fi,Action|visually stunning,intense|Japanese
Ghost in the Shell (1995)|Animation,Sci-Fi,Thriller|philosophical,stylish|Japanese
Perfect Blue (1997)|Animation,Thriller,Horror|psychological,disturbing|Japanese
Your Name (2016)|Animation,Drama,Romance,Fantasy|romantic,emotional|Japanese
Weathering with You (2019)|Animation,Drama,Romance,Fantasy|romantic,visually stunning|Japanese
Crouching Tiger Hidden Dragon (2000)|Action,Drama,Romance|stylish,poetic|Mandarin
Farewell My Concubine (1993)|Drama,History,Romance|epic,emotional|Mandarin
In the Mood for Love (2000)|Drama,Romance|romantic,stylish|Cantonese
Chungking Express (1994)|Drama,Comedy,Romance|stylish,romantic|Cantonese
Hero (2002)|Action,Drama,Adventure|visually stunning,epic|Mandarin
House of Flying Daggers (2004)|Action,Drama,Romance|visually stunning,romantic|Mandarin
Kung Fu Hustle (2004)|Action,Comedy,Fantasy|fun,stylish|Cantonese
A Better Tomorrow (1986)|Action,Crime,Drama|stylish,violent|Cantonese
Infernal Affairs (2002)|Crime,Drama,Thriller|tense,clever|Cantonese
Lagaan (2001)|Drama,Sport,Musical|inspiring,epic|Hindi
3 Idiots (2009)|Comedy,Drama|heartwarming,witty|Hindi
Dangal (2016)|Drama,Sport,Biography|inspiring,emotional|Hindi
PK (2014)|Comedy,Drama,Sci-Fi|thought-provoking,witty|Hindi
Taare Zameen Par (2007)|Drama,Family|emotional,inspiring|Hindi
Ratsasan (2018)|Thriller,Crime,Mystery|tense,psychological|Tamil
Jallikattu (2019)|Drama,Thriller|visceral,raw|Malayalam
Aladdin (1992)|Animation,Adventure,Family,Musical|charming,romantic|English
Mulan (1998)|Animation,Adventure,Drama,Family|inspiring,epic|English
Tarzan (1999)|Animation,Adventure,Family|adventurous,emotional|English
Lilo & Stitch (2002)|Animation,Comedy,Family,Sci-Fi|heartwarming,fun|English
Finding Nemo (2003)|Animation,Adventure,Comedy,Family|heartwarming,adventurous|English
The Incredibles (2004)|Animation,Action,Adventure,Family|fun,stylish|English
Ratatouille (2007)|Animation,Comedy,Family|charming,witty|English
WALL-E (2008)|Animation,Sci-Fi,Adventure,Family|sweet,thought-provoking|English
Coco (2017)|Animation,Adventure,Family,Fantasy|emotional,colorful|English
Inside Out (2015)|Animation,Adventure,Comedy,Drama|emotional,clever|English
Zootopia (2016)|Animation,Adventure,Comedy,Family|witty,satirical|English
Moana (2016)|Animation,Adventure,Family,Musical|inspiring,adventurous|English
Frozen (2013)|Animation,Adventure,Family,Musical|heartwarming,empowering|English
Tangled (2010)|Animation,Adventure,Family,Musical|charming,romantic|English
Shrek (2001)|Animation,Adventure,Comedy,Family|witty,fun|English
Shrek 2 (2004)|Animation,Adventure,Comedy,Family|witty,fun|English
Monsters Inc (2001)|Animation,Comedy,Family,Fantasy|heartwarming,fun|English
Monsters University (2013)|Animation,Comedy,Family|fun,heartwarming|English
Brave (2012)|Animation,Adventure,Family,Fantasy|empowering,emotional|English
The Iron Giant (1999)|Animation,Adventure,Family,Sci-Fi|emotional,heartwarming|English
Spider-Man: Into the Spider-Verse (2018)|Animation,Action,Adventure,Sci-Fi|stylish,inspiring|English
The Dark Knight (2008)|Action,Crime,Drama,Thriller|dark,intense|English
The Dark Knight Rises (2012)|Action,Crime,Drama,Thriller|epic,intense|English
Batman Begins (2005)|Action,Crime,Drama|dark,origin|English
Iron Man (2008)|Action,Adventure,Sci-Fi|fun,stylish|English
The Avengers (2012)|Action,Adventure,Sci-Fi|epic,fun|English
Black Panther (2018)|Action,Adventure,Sci-Fi|powerful,stylish|English
Guardians of the Galaxy (2014)|Action,Adventure,Sci-Fi,Comedy|fun,nostalgic|English
Thor: Ragnarok (2017)|Action,Adventure,Sci-Fi,Comedy|fun,colorful|English
Captain America: The Winter Soldier (2014)|Action,Adventure,Sci-Fi,Thriller|tense,stylish|English
Logan (2017)|Action,Drama,Sci-Fi|emotional,gritty|English
Deadpool (2016)|Action,Comedy,Adventure|raunchy,witty|English
John Wick (2014)|Action,Thriller,Crime|stylish,violent|English
John Wick: Chapter 2 (2017)|Action,Crime,Thriller|stylish,violent|English
Mission: Impossible (1996)|Action,Adventure,Thriller|thrilling,clever|English
Mission: Impossible - Fallout (2018)|Action,Adventure,Thriller|thrilling,intense|English
The Bourne Identity (2002)|Action,Mystery,Thriller|tense,smart|English
The Bourne Ultimatum (2007)|Action,Thriller|tense,thrilling|English
Skyfall (2012)|Action,Adventure,Thriller|stylish,emotional|English
Casino Royale (2006)|Action,Adventure,Thriller|stylish,tense|English
GoldenEye (1995)|Action,Adventure,Thriller|fun,stylish|English
Léon: The Professional (1994)|Action,Crime,Drama|stylish,emotional|English
Kill Bill: Vol. 1 (2003)|Action,Thriller,Crime|stylish,violent|English
Kill Bill: Vol. 2 (2004)|Action,Thriller,Crime|stylish,emotional|English
Sin City (2005)|Crime,Thriller,Neo-Noir|stylish,violent|English
The Town (2010)|Crime,Drama,Thriller|tense,gritty|English
Sicario (2015)|Crime,Drama,Thriller|tense,grim|English
Prisoners (2013)|Crime,Drama,Mystery,Thriller|tense,disturbing|English
Zodiac (2007)|Crime,Drama,Mystery,Thriller|tense,methodical|English
Gone Girl (2014)|Drama,Mystery,Thriller|twisted,tense|English
The Girl with the Dragon Tattoo (2011)|Drama,Mystery,Thriller|dark,tense|English
Shutter Island (2010)|Mystery,Thriller,Drama|twisted,atmospheric|English
Memento (2000)|Mystery,Thriller|mind-bending,tense|English
The Prestige (2006)|Drama,Mystery,Sci-Fi|clever,twisted|English
Interstellar (2014)|Adventure,Drama,Sci-Fi|emotional,epic|English
The Martian (2015)|Adventure,Sci-Fi,Drama|inspiring,witty|English
Ex Machina (2014)|Drama,Sci-Fi,Thriller|thought-provoking,tense|English
Blade Runner 2049 (2017)|Sci-Fi,Drama,Mystery|visually stunning,contemplative|English
Dune (2021)|Sci-Fi,Adventure,Drama|epic,visually stunning|English
Everything Everywhere All at Once (2022)|Sci-Fi,Action,Adventure,Comedy|chaotic,emotional|English
The Batman (2022)|Action,Crime,Drama,Thriller|dark,noir|English
Top Gun: Maverick (2022)|Action,Drama|thrilling,nostalgic|English
Dune: Part Two (2024)|Sci-Fi,Adventure,Drama|epic,visually stunning|English
Oppenheimer (2023)|Drama,History,Biography|intense,epic|English
Barbie (2023)|Comedy,Adventure,Fantasy|satirical,fun|English
Past Lives (2023)|Drama,Romance|contemplative,emotional|English
The Holdovers (2023)|Comedy,Drama|warm,witty|English
Poor Things (2023)|Comedy,Drama,Sci-Fi,Romance|quirky,stylish|English
Killers of the Flower Moon (2023)|Drama,Crime,History|epic,grim|English
The Banshees of Inisherin (2022)|Comedy,Drama|dark humor,emotional|English
Tár (2022)|Drama,Music|complex,intense|English
The Fabelmans (2022)|Drama|autobiographical,emotional|English
Aftersun (2022)|Drama|quiet,emotional|English
EEAAO (2022)|Sci-Fi,Action,Comedy,Drama|chaotic,emotional|English
Nomadland (2020)|Drama|contemplative,emotional|English
Minari (2020)|Drama|quiet,emotional|English
Sound of Metal (2019)|Drama,Music|raw,emotional|English
The Father (2020)|Drama,Mystery|heartbreaking,clever|English
Promising Young Woman (2020)|Crime,Drama,Thriller|dark,satirical|English
Judas and the Black Messiah (2021)|Drama,History,Biography|powerful,tense|English
The Power of the Dog (2021)|Drama,Western|slow-burn,tense|English
West Side Story (2021)|Musical,Drama,Romance|romantic,stylish|English
Licorice Pizza (2021)|Comedy,Drama,Romance|nostalgic,charming|English
Don't Look Up (2021)|Comedy,Drama,Sci-Fi|satirical,dark humor|English
The French Dispatch (2021)|Comedy,Drama,Romance|whimsical,stylish|English
Spencer (2021)|Drama,Biography,History|claustrophobic,emotional|English
The Lost Daughter (2021)|Drama,Mystery|unsettling,complex|English
C'mon C'mon (2021)|Drama|quiet,emotional|English
Red Rocket (2021)|Comedy,Drama|dark humor,gritty|English
The Worst Person in the World (2021)|Comedy,Drama,Romance|witty,emotional|Norwegian
Drive My Car (2021)|Drama|contemplative,emotional|Japanese
Petite Maman (2021)|Drama,Fantasy|gentle,emotional|French
Titane (2021)|Horror,Sci-Fi,Drama|disturbing,visceral|French
The Green Knight (2021)|Adventure,Drama,Fantasy|atmospheric,meditative|English
The Northman (2022)|Action,Drama,Adventure|visceral,epic|English
The Unbearable Weight of Massive Talent (2022)|Comedy,Action|meta,fun|English
The Menu (2022)|Comedy,Horror,Thriller|dark humor,tense|English
Glass Onion (2022)|Comedy,Mystery,Thriller|clever,fun|English
Triangle of Sadness (2022)|Comedy,Drama|satirical,dark humor|English
Women Talking (2022)|Drama|powerful,emotional|English
She Said (2022)|Drama,History,Thriller|tense,inspiring|English
Elvis (2022)|Drama,Biography,Music|stylish,emotional|English
Avatar: The Way of Water (2022)|Sci-Fi,Adventure,Action|visually stunning,emotional|English
Black Adam (2022)|Action,Adventure,Fantasy|action-packed,fun|English
The Whale (2022)|Drama|emotional,raw|English
Till (2022)|Drama,History,Biography|powerful,emotional|English
The Woman King (2022)|Action,Drama,History|powerful,epic|English
RRR (2022)|Action,Drama,War|epic,over-the-top|Telugu
All Quiet on the Western Front (2022)|Drama,War|grim,visceral|German
Decision to Leave (2022)|Drama,Mystery,Romance|stylish,romantic|Korean
Broker (2022)|Drama|emotional,contemplative|Korean
Return to Seoul (2022)|Drama|contemplative,emotional|French
Saint Omer (2022)|Drama|contemplative,powerful|French
Close (2022)|Drama|emotional,devastating|French
EO (2022)|Drama|contemplative,emotional|Polish
Argentina 1985 (2022)|Drama,History,Thriller|tense,inspiring|Spanish
Bardo (2022)|Drama,Comedy,Fantasy|surreal,personal|Spanish
Alcarràs (2022)|Drama|quiet,emotional|Catalan
Pacifiction (2022)|Drama,Thriller|atmospheric,paranoid|French
Aftersun (2022)|Drama|quiet,emotional|English
Living (2022)|Drama|quiet,emotional|English
The Quiet Girl (2022)|Drama|quiet,emotional|Irish
Marcel the Shell with Shoes On (2021)|Animation,Comedy,Family,Drama|charming,heartwarming|English
Guillermo del Toro's Pinocchio (2022)|Animation,Drama,Family,Fantasy|dark,emotional|English
Turning Red (2022)|Animation,Comedy,Family|charming,emotional|English
Encanto (2021)|Animation,Comedy,Family,Musical|colorful,heartwarming|English
Luca (2021)|Animation,Adventure,Comedy,Family|charming,nostalgic|English
Soul (2020)|Animation,Comedy,Drama,Family|contemplative,emotional|English
Onward (2020)|Animation,Adventure,Comedy,Family|emotional,fun|English
Frozen II (2019)|Animation,Adventure,Family,Fantasy|emotional,epic|English
Toy Story 4 (2019)|Animation,Adventure,Comedy,Family|emotional,heartwarming|English
Napoleon Dynamite (2004)|Comedy|quirky,fun|English
Superbad (2007)|Comedy|raunchy,fun|English
Bridesmaids (2011)|Comedy,Romance|raunchy,heartwarming|English
The Hangover (2009)|Comedy|raunchy,fun|English
Anchorman (2004)|Comedy|silly,witty|English
Step Brothers (2008)|Comedy|raunchy,fun|English
Tropic Thunder (2008)|Comedy,Action,War|dark humor,witty|English
Borat (2006)|Comedy|satirical,shocking|English
Office Space (1999)|Comedy|relatable,witty|English
Groundhog Day (1993)|Comedy,Romance,Fantasy|witty,heartwarming|English
When Harry Met Sally (1989)|Comedy,Romance|witty,romantic|English
Sleepless in Seattle (1993)|Comedy,Romance,Drama|charming,romantic|English
You've Got Mail (1998)|Comedy,Romance|charming,romantic|English
Notting Hill (1999)|Comedy,Romance|charming,romantic|English
Love Actually (2003)|Comedy,Romance,Drama|heartwarming,romantic|English
Four Weddings and a Funeral (1994)|Comedy,Romance|witty,romantic|English
The Full Monty (1997)|Comedy,Drama|heartwarming,uplifting|English
Billy Elliot (2000)|Drama,Comedy,Music|inspiring,emotional|English
Slumdog Millionaire (2008)|Drama,Romance|uplifting,emotional|English
Babel (2006)|Drama|complex,emotional|English
21 Grams (2003)|Drama,Thriller,Mystery|heavy,emotional|English
The Constant Gardener (2005)|Drama,Thriller,Romance|tense,emotional|English
Children of Men (2006)|Sci-Fi,Drama,Thriller|bleak,tense|English
V for Vendetta (2005)|Action,Drama,Thriller|rebellious,stylish|English
Watchmen (2009)|Action,Drama,Sci-Fi|dark,stylish|English
Source Code (2011)|Sci-Fi,Thriller,Mystery|tense,clever|English
Looper (2012)|Sci-Fi,Action,Thriller|mind-bending,tense|English
District 9 (2009)|Sci-Fi,Thriller,Drama|gritty,thought-provoking|English
Moon (2009)|Sci-Fi,Drama,Mystery|contemplative,lonely|English
Sunshine (2007)|Sci-Fi,Thriller,Adventure|tense,visually stunning|English
Annihilation (2018)|Horror,Sci-Fi,Adventure|trippy,unsettling|English
Under the Skin (2013)|Horror,Sci-Fi,Drama|unsettling,atmospheric|English
The Witch (2015)|Horror,Drama|atmospheric,unsettling|English
Hereditary (2018)|Horror,Drama,Mystery|disturbing,tense|English
Midsommar (2019)|Horror,Drama,Mystery|unsettling,visceral|English
Get Out (2017)|Horror,Thriller,Mystery|tense,satirical|English
The Babadook (2014)|Horror,Drama|unsettling,emotional|English
Let the Right One In (2008)|Horror,Drama,Romance|atmospheric,emotional|Swedish
The Orphanage (2007)|Horror,Drama,Mystery|atmospheric,emotional|Spanish
Rec (2007)|Horror,Thriller|tense,claustrophobic|Spanish
The Devil's Backbone (2001)|Horror,Drama,War|atmospheric,emotional|Spanish
Open Your Eyes (1997)|Drama,Sci-Fi,Thriller,Mystery|mind-bending,romantic|Spanish
The Secret in Their Eyes (2009)|Drama,Mystery,Thriller|tense,emotional|Spanish
Wild Tales (2014)|Comedy,Drama,Thriller|dark humor,anthology|Spanish
The Sea Inside (2004)|Drama,Biography,Romance|emotional,contemplative|Spanish
Volver (2006)|Comedy,Drama|warm,emotional|Spanish
Talk to Her (2002)|Drama,Romance|emotional,unusual|Spanish
Bad Education (2004)|Drama,Thriller|complex,unsettling|Spanish
Pain and Glory (2019)|Drama|autobiographical,emotional|Spanish
Parallel Mothers (2021)|Drama|emotional,complex|Spanish
"""

def parse_extra(line):
    line = line.strip()
    if not line:
        return None
    parts = line.split("|")
    if len(parts) < 4:
        return None
    title = parts[0].strip()
    year_match = re.search(r"\((\d{4})\)\s*$", title)
    if year_match:
        year = int(year_match.group(1))
        title = re.sub(r"\s*\(\d{4}\)\s*$", "", title).strip()
    else:
        year = 2000
    genres = [g.strip() for g in parts[1].split(",")]
    moods = [m.strip() for m in parts[2].split(",")]
    language = parts[3].strip()
    return {"title": title, "year": year, "genre": genres, "mood": moods, "language": language}

def main():
    movies = []
    seen = set()

    for line in CORPORA_RAW.strip().split("\n"):
        if not line.strip():
            continue
        m = parse_line(line)
        if m and m["title"] not in seen:
            movies.append(m)
            seen.add(m["title"])

    for line in EXTRA_MOVIES.strip().split("\n"):
        if not line.strip():
            continue
        m = parse_extra(line)
        if m and m["title"] not in seen:
            movies.append(m)
            seen.add(m["title"])

    # Fix a few titles that had year in corpora format in EXTRA
    for m in movies:
        if "(" in m["title"] and ")" in m["title"]:
            import re
            if re.search(r"\(\d{4}\)", m["title"]):
                m["title"] = re.sub(r"\s*\(\d{4}\)\s*$", "", m["title"]).strip()

    # Take first 500
    movies = movies[:500]
    print(f"Collected {len(movies)} movies for movies.json")

    out = [{"title": m["title"], "genre": m["genre"], "year": m["year"], "mood": m["mood"], "language": m["language"]} for m in movies]
    with open("movies.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Written {len(out)} movies to movies.json")

if __name__ == "__main__":
    main()
