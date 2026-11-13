from vkbottle import BaseStateGroup

class CreateEventState(BaseStateGroup):
    TITLE = "title"
    MAX_VOLUNTEERS = "max_volunteers"
    GENDER = "gender"
    DATE = "date"
    TIME_START = "time_start"
    TIME_END = "time_end"
    LOCATION = "location"
    DESCRIPTION = "description"
    BONUS = "bonus"
    CHAT_LINK = "chat_link"
    CONFIRMATION = "confirmation"
    CHOOSING_TYPE = "choosing_type"

class AnnouncementState(BaseStateGroup):
    PHOTO = "ann_photo"
    TITLE = "ann_title"
    TEXT = "ann_text"
    PREVIEW = "ann_preview"