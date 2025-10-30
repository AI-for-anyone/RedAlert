from mofa.agent_build.base.base_agent import MofaAgent, run_agent
import time

@run_agent
def run(agent: MofaAgent):
    try:
        data = agent.receive_parameter('data')
        print(f"{time.strftime('%H:%M:%S')}:{data}")

    except Exception as e:
        error_message = f"An exception occurred: {str(e)}"

        # Use MofaAgent's correct logging method
        agent.write_log(message=error_message, level='ERROR')

def main():
    agent = MofaAgent(agent_name='ra-show')
    run(agent=agent)

if __name__ == "__main__":
    main()