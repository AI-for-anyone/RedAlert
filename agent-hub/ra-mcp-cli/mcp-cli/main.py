from mofa.agent_build.base.base_agent import MofaAgent, run_agent

@run_agent
def run(agent: MofaAgent):
    try:
        user_input = agent.receive_parameter('data')
        agent.write_log(message=f"Received input: {user_input}")
        print(f"show-result data == {user_input}")

    except Exception as e:
        error_message = f"An exception occurred: {str(e)}"

        # Use MofaAgent's correct logging method
        agent.write_log(message=error_message, level='ERROR')


def main():
    agent = MofaAgent(agent_name='show-result')
    run(agent=agent)

if __name__ == "__main__":
    main()