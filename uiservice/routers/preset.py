import json

import config
import requests as r

import container
from extras import log_erroneous_answer

PRESET_OVERRIDE_WARNING_MESSAGE = "Your preset name is the same as global preset. It will override global preset."
PRESET_ALREADY_EXISTS = "Preset already exists. Please, delete existing preset or choose another name (wisely)."
NO_CHANNELS_PASSED_MESSAGE = "No channels selected."


async def send_initial_message(user_id: str, channel_id: str) -> None:
    base_url = f"http://{config.DB_URL}/category/"
    try:
        answer = r.get(base_url, params={"user_id": user_id, "include_global": False}, timeout=10)
    except r.Timeout:
        await container.slacker.post_to_channel(
            channel_id=channel_id,
            text="Received timeout during database interaction. Please, try later."
        )
        return

    presets = answer.json()
    for x in presets:
        x['text_channel_ids'] = ", ".join(f"<#{c}>" for c in x.get('channel_ids'))

    template = container.jinja_env.get_template("preset_list.json")
    result = template.render(presets=presets)
    await container.slacker.post_to_channel(channel_id=channel_id, blocks=result, ephemeral=True, user_id=user_id)


async def preset_interaction_eligibility(data: dict):
    return (data.get("type", "") == "block_actions" and
            data.get("actions", [{}])[0].get("action_id", "").startswith("preset")) or \
           (data.get("type", "") == "view_submission" and
            data.get("view", {}).get("callback_id", "") == "preset_new_submission")


async def preset_interaction(data: dict):
    action_id = data.get("actions", [{}])[0].get("action_id", "")
    channel_id = data.get('channel', {}).get("id", "")
    user_id = data.get("user", {}).get("id", "")

    if action_id == "preset_new":
        await __show_preset_creation(data)
    elif data.get("type", "") == "view_submission" and \
            data.get("view", {}).get("callback_id", "") == "preset_new_submission":
        await __process_preset_creation(data, user_id)
    elif action_id == "preset_delete":
        await __process_preset_deletion(data, channel_id, user_id)
    else:
        container.logger.warning(f"Unknown preset interaction message: {data}")


async def __show_preset_creation(data: dict):
    trigger_id = data.get("trigger_id", "")
    template = container.jinja_env.get_template("preset_new.json")
    result = template.render()
    await container.slacker.open_view(trigger_id=trigger_id, view=result)


async def __process_preset_deletion(data: dict, channel_id: str, user_id: str):
    preset_name = data.get("actions", [{}])[0].get("value", "")
    base_url = f"http://{config.DB_URL}/category/"

    if preset_name is None:
        await container.slacker.post_to_channel(channel_id=channel_id, text=(
            "Preset name to delete should be explicitly specified. "
            "Please specify preset name or type `help presets` to get additional information."
        ))
        return

    answer = r.delete(base_url, params={'name': preset_name, 'user_id': user_id}, timeout=10)
    if answer.status_code == 200:
        await container.slacker.post_to_channel(channel_id=channel_id,
                                                text=f"Preset {preset_name} successfully deleted.")
    else:
        container.logger.error(answer.text)
        await container.slacker.post_to_channel(channel_id=channel_id, text=(
            f"Some error occurred. Preset {preset_name} possibly is not deleted. "
            f"Please, check with `presets` and contact developers team. Thanks."
        ))


async def __process_preset_creation(data: dict, user_id: str):
    base_url = f"http://{config.DB_URL}/category/"

    # get preset name and channels
    data = data.get("view", {}).get("state", {}).get("values", {})
    preset_name = data.get("preset_name", {}).get("title", {}).get("value", "")
    channels = data.get("channels_selector", {}).get("channels", {}).get("selected_channels", [])

    # check that preset_name does not exist and channels are not empty
    try:
        answer = r.get(base_url, params={"user_id": user_id, "include_global": False}, timeout=10)
    except r.Timeout:
        await container.slacker.post_to_channel(
            channel_id=user_id,
            text="Received timeout during database interaction. Please, try later."
        )
        return

    if preset_name in {x.get("name", "") for x in answer.json()}:
        await container.slacker.post_to_channel(channel_id=user_id, text=PRESET_ALREADY_EXISTS)
        return

    if not channels:
        await container.slacker.post_to_channel(channel_id=user_id, text=NO_CHANNELS_PASSED_MESSAGE)
        return

    # check whether user will override global categories
    try:
        answer = r.get(base_url, params={"include_global": True}, timeout=10)
    except r.Timeout:
        await container.slacker.post_to_channel(
            channel_id=user_id,
            text="Received timeout during database interaction. Please, try later."
        )
        return

    user_answer = ""
    if preset_name in {x.name for x in answer.json()}:
        user_answer += PRESET_OVERRIDE_WARNING_MESSAGE
        user_answer += "\n"

    answer = r.put(base_url, params={'user_id': user_id, 'name': preset_name}, data=json.dumps(channels), timeout=10)
    if answer.status_code != 200:
        log_erroneous_answer(answer)
        user_answer += answer.text
    else:
        user_answer += f"Successfully created preset {preset_name}."

    await container.slacker.post_to_channel(channel_id=user_id, text=user_answer)