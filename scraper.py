import requests
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Configuration
TEAM_ID = "1441922147"
SEASON_ID = "842514138"
GB_ID = "36"

SCHEDULE_URL = f"https://www.trackwrestling.com/tw/seasons/LoadBalance.jsp?seasonId={SEASON_ID}&gbId={GB_ID}&pageName=TeamSchedule.jsp;teamId={TEAM_ID}"

def scrape_team_schedule():
    """
    Scrape the team schedule to get list of match IDs
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        print(f"Fetching schedule from: {SCHEDULE_URL}")
        response = requests.get(SCHEDULE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"Response status: {response.status_code}")
        
        # Save raw HTML for debugging
        with open('debug_schedule_raw.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Saved raw HTML to debug_schedule_raw.html")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Save prettified HTML
        with open('debug_schedule.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("Saved prettified HTML to debug_schedule.html")
        
        # Find all links containing dualId
        matches = []
        all_links = soup.find_all('a', href=True)
        print(f"Found {len(all_links)} total links on page")
        
        for link in all_links:
            href = link.get('href', '')
            
            # Look for dualId in the URL
            if 'dualId=' in href:
                dual_match = re.search(r'dualId=(\d+)', href)
                if dual_match:
                    dual_id = dual_match.group(1)
                    
                    # Build full URL if it's a relative link
                    if not href.startswith('http'):
                        href = f"https://www.trackwrestling.com/tw/seasons/{href}"
                    
                    # Get opponent name from link text or nearby elements
                    opponent = link.get_text(strip=True)
                    
                    # Try to find date and location in parent row
                    parent = link.find_parent('tr')
                    date_text = ''
                    location_text = ''
                    
                    if parent:
                        cells = parent.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            # Usually date is first, opponent/link is second
                            date_text = cells[0].get_text(strip=True)
                            if len(cells) >= 3:
                                location_text = cells[2].get_text(strip=True)
                    
                    match_info = {
                        'dualId': dual_id,
                        'opponent': opponent or f"Match {dual_id}",
                        'date': date_text,
                        'location': location_text,
                        'url': f"https://www.trackwrestling.com/tw/seasons/LoadBalance.jsp?seasonId={SEASON_ID}&pageName=DualMatches.jsp&dualId={dual_id}"
                    }
                    
                    matches.append(match_info)
                    print(f"Found match: {match_info['opponent']} on {match_info['date']} (ID: {dual_id})")
        
        print(f"\nTotal matches found: {len(matches)}")
        
        # If no matches found, create dummy data for testing
        if len(matches) == 0:
            print("WARNING: No matches found! Creating sample data for testing...")
            matches = [{
                'dualId': '0000000000',
                'opponent': 'Sample Match (No data available)',
                'date': 'TBD',
                'location': 'TBD',
                'url': SCHEDULE_URL
            }]
        
        return matches
        
    except Exception as e:
        print(f"Error scraping schedule: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty list with sample data
        return [{
            'dualId': '0000000000',
            'opponent': 'Error loading matches',
            'date': 'TBD',
            'location': 'TBD',
            'url': SCHEDULE_URL
        }]

def scrape_match_details(dual_id):
    """
    Scrape detailed match results from a specific dual match
    """
    try:
        match_url = f"https://www.trackwrestling.com/tw/seasons/LoadBalance.jsp?seasonId={SEASON_ID}&pageName=DualMatches.jsp&dualId={dual_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        print(f"  Fetching match details for dualId: {dual_id}")
        response = requests.get(match_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Save debug file for first match
        if dual_id == scrape_match_details.first_match:
            with open('debug_match.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print(f"  Saved match HTML to debug_match.html")
        
        # Look for bout data in tables
        bouts = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                
                # Skip header rows
                if len(cells) < 3:
                    continue
                
                # Try to identify weight class (usually first column)
                weight_text = cells[0].get_text(strip=True)
                
                # Check if this looks like a weight class
                if re.search(r'\d{2,3}', weight_text):
                    bout = {
                        'weight': weight_text,
                        'wrestler1': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                        'wrestler2': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                        'result': cells[3].get_text(strip=True) if len(cells) > 3 else ''
                    }
                    
                    if bout['wrestler1'] or bout['wrestler2']:
                        bouts.append(bout)
        
        print(f"  Found {len(bouts)} bouts for match {dual_id}")
        
        return {
            'dualId': dual_id,
            'bouts': bouts
        }
        
    except Exception as e:
        print(f"  Error scraping match {dual_id}: {e}")
        return {
            'dualId': dual_id,
            'bouts': []
        }

# Track first match for debugging
scrape_match_details.first_match = None

def extract_roster_from_matches(all_matches):
    """
    Extract unique wrestlers from all match data to build roster
    """
    wrestlers_dict = {}
    
    for match in all_matches:
        if 'details' in match and 'bouts' in match['details']:
            for bout in match['details']['bouts']:
                wrestler_name = bout.get('wrestler1', '').strip()
                weight = bout.get('weight', '').replace('lbs', '').strip()
                
                # Extract just the number from weight
                weight_match = re.search(r'(\d{2,3})', weight)
                if weight_match:
                    weight = weight_match.group(1)
                
                if wrestler_name and wrestler_name != 'BYE':
                    if wrestler_name not in wrestlers_dict:
                        wrestlers_dict[wrestler_name] = {
                            'name': wrestler_name,
                            'weight': weight,
                            'matches': 0,
                            'wins': 0
                        }
                    
                    wrestlers_dict[wrestler_name]['matches'] += 1
                    
                    # Count wins
                    result = bout.get('result', '').lower()
                    if any(x in result for x in ['win', 'w ', 'tf', 'pin', 'dec', 'md', 'fall']):
                        wrestlers_dict[wrestler_name]['wins'] += 1
    
    # Convert to list and add records
    roster = []
    for wrestler in wrestlers_dict.values():
        losses = wrestler['matches'] - wrestler['wins']
        wrestler['record'] = f"{wrestler['wins']}-{losses}"
        roster.append(wrestler)
    
    # Sort by weight class
    roster.sort(key=lambda x: int(x['weight']) if x['weight'].isdigit() else 999)
    
    return roster

def main():
    """
    Main scraping function
    """
    print("=" * 70)
    print("TrackWrestling Scraper for Shawnee Wrestling")
    print("=" * 70)
    print(f"Team ID: {TEAM_ID}")
    print(f"Season ID: {SEASON_ID}")
    print("=" * 70)
    
    # Step 1: Get schedule with match IDs
    print("\n[1/4] Scraping team schedule...")
    schedule_data = scrape_team_schedule()
    print(f"✓ Found {len(schedule_data)} matches in schedule")
    
    # Step 2: Scrape details for each match (limit to avoid timeouts)
    print("\n[2/4] Scraping match details...")
    all_match_details = []
    max_matches = min(len(schedule_data), 15)  # Limit to 15 matches
    
    if schedule_data and schedule_data[0]['dualId'] != '0000000000':
        scrape_match_details.first_match = schedule_data[0]['dualId']
        
        for i, match in enumerate(schedule_data[:max_matches], 1):
            print(f"\n  Match {i}/{max_matches}: {match['opponent']}")
            details = scrape_match_details(match['dualId'])
            match['details'] = details
            all_match_details.append(match)
    else:
        all_match_details = schedule_data
    
    print(f"\n✓ Successfully scraped {len(all_match_details)} match details")
    
    # Step 3: Extract roster from match data
    print("\n[3/4] Building roster from match data...")
    roster_data = extract_roster_from_matches(all_match_details)
    print(f"✓ Extracted {len(roster_data)} wrestlers")
    
    # Step 4: Format schedule for display
    print("\n[4/4] Formatting data for web display...")
    formatted_schedule = []
    for match in schedule_data:
        formatted_schedule.append({
            'date': match.get('date', 'TBD'),
            'opponent': match.get('opponent', 'Unknown'),
            'location': match.get('location', 'TBD'),
            'result': match.get('result', '-'),
            'dualId': match['dualId'],
            'url': match['url']
        })
    
    # Create data package
    data_package = {
        'last_updated': datetime.now().isoformat(),
        'team_id': TEAM_ID,
        'season_id': SEASON_ID,
        'roster': roster_data,
        'schedule': formatted_schedule,
        'match_details': all_match_details
    }
    
    # Save to JSON files
    print("\nSaving data files...")
    
    with open('data/roster.json', 'w') as f:
        json.dump(roster_data, f, indent=2)
    print("✓ Saved data/roster.json")
    
    with open('data/schedule.json', 'w') as f:
        json.dump(formatted_schedule, f, indent=2)
    print("✓ Saved data/schedule.json")
    
    with open('data/complete.json', 'w') as f:
        json.dump(data_package, f, indent=2)
    print("✓ Saved data/complete.json")
    
    with open('data/match_details.json', 'w') as f:
        json.dump(all_match_details, f, indent=2)
    print("✓ Saved data/match_details.json")
    
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE!")
    print("=" * 70)
    print(f"📊 Roster: {len(roster_data)} wrestlers")
    print(f"📅 Schedule: {len(formatted_schedule)} matches")
    print(f"🤼 Match details: {len(all_match_details)} matches with bout data")
    print("=" * 70)

if __name__ == "__main__":
    main()
