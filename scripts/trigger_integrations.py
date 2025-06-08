#!/usr/bin/env python3
# NetProbe Pi - Webhook and MQTT Integration

import os
import sys
import json
import logging
import argparse
import requests
import datetime
import paho.mqtt.client as mqtt
from pathlib import Path

# Add the src directory to the path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Import core modules
from src.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/netprobe/integrations.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='NetProbe Pi - Integration Trigger')
    parser.add_argument('--event', type=str, required=True, help='Event name')
    parser.add_argument('--data', type=str, help='JSON data for the event')
    parser.add_argument('--config', type=str, default='/etc/netprobe/config.yaml', 
                        help='Path to configuration file')
    
    return parser.parse_args()

def send_webhook(url, data):
    """Send webhook to the specified URL."""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Webhook sent successfully to {url}")
            return True
        else:
            logger.error(f"Failed to send webhook to {url}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending webhook to {url}: {str(e)}")
        return False

def send_mqtt(broker, topic, data, username=None, password=None):
    """Send MQTT message to the specified broker and topic."""
    try:
        client = mqtt.Client()
        
        # Set username and password if provided
        if username and password:
            client.username_pw_set(username, password)
        
        # Connect to the broker
        client.connect(broker, 1883, 60)
        
        # Send message
        result = client.publish(topic, json.dumps(data))
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"MQTT message sent successfully to {broker}/{topic}")
            return True
        else:
            logger.error(f"Failed to send MQTT message to {broker}/{topic}: {result.rc}")
            return False
    except Exception as e:
        logger.error(f"Error sending MQTT message to {broker}/{topic}: {str(e)}")
        return False

def main():
    """Main entry point."""
    args = parse_args()
    
    # Load configuration
    try:
        config = Config(args.config)
        logger.info(f"Configuration loaded from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Parse event data
    event_data = {}
    if args.data:
        try:
            event_data = json.loads(args.data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON data")
            sys.exit(1)
    
    # Add event metadata
    event_data.update({
        'event': args.event,
        'timestamp': datetime.datetime.now().isoformat(),
        'device': config.get('device.name', 'netprobe')
    })
    
    # Process webhooks
    webhooks = config.get('integrations.webhooks', [])
    for webhook in webhooks:
        if webhook.get('enabled', True) and webhook.get('url'):
            events = webhook.get('events', ['*'])
            if args.event in events or '*' in events:
                send_webhook(webhook['url'], event_data)
    
    # Process MQTT
    mqtt_config = config.get('integrations.mqtt', {})
    if mqtt_config.get('enabled', False) and mqtt_config.get('broker'):
        broker = mqtt_config['broker']
        topic = mqtt_config.get('topic', f"netprobe/{config.get('device.name', 'netprobe')}")
        username = mqtt_config.get('username')
        password = mqtt_config.get('password')
        
        send_mqtt(broker, f"{topic}/{args.event}", event_data, username, password)
    
    logger.info(f"Event {args.event} processed successfully")

if __name__ == "__main__":
    main()
