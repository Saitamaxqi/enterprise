import { projectTaskCalendarView } from "@project/views/project_task_calendar/project_task_calendar_view";
import { ProjectEnterpriseTaskCalendarModel } from "./project_task_calendar_model";
import { ProjectTaskSearchModel } from "../project_task_search_model";

projectTaskCalendarView.SearchModel = ProjectTaskSearchModel;
projectTaskCalendarView.Model = ProjectEnterpriseTaskCalendarModel;
